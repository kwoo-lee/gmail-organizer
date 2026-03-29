import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
log = logging.getLogger(__name__)


class GmailClient:
    def __init__(self):
        self.service = self._authenticate()
        self._label_cache = {}

    def _authenticate(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('secrets/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as f:
                f.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def get_current_history_id(self):
        profile = self.service.users().getProfile(userId='me').execute()
        return profile['historyId']

    def get_new_messages(self, start_history_id):
        """startHistoryId 이후에 추가된 새 메시지 목록과 최신 historyId 반환"""
        try:
            response = self.service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded']
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                # historyId 만료 시 현재 ID로 리셋
                log.warning("historyId 만료, 현재 시점으로 리셋합니다.")
                new_id = self.get_current_history_id()
                return [], new_id
            raise

        new_history_id = response.get('historyId', start_history_id)
        messages = []
        for history in response.get('history', []):
            for msg_added in history.get('messagesAdded', []):
                messages.append(msg_added['message'])

        return messages, new_history_id

    def get_message_details(self, message_id):
        """메시지의 발신자·제목·라벨 정보 반환 (본문 제외)"""
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='metadata',
            metadataHeaders=['From', 'Subject']
        ).execute()

        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        return {
            'id': message_id,
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'label_ids': msg.get('labelIds', [])
        }

    def get_or_create_label(self, name):
        """라벨 ID 반환. 존재하지 않으면 생성"""
        if name in self._label_cache:
            return self._label_cache[name]

        labels = self.service.users().labels().list(userId='me').execute()
        for label in labels.get('labels', []):
            if label['name'] == name:
                self._label_cache[name] = label['id']
                return label['id']

        created = self.service.users().labels().create(
            userId='me',
            body={'name': name}
        ).execute()
        log.info(f"새 라벨 생성: '{name}'")
        self._label_cache[name] = created['id']
        return created['id']

    def apply_actions(self, message_id, label_name=None, mark_read=False):
        """라벨 추가 및/또는 읽음 처리"""
        add_labels = []
        remove_labels = []

        if label_name:
            add_labels.append(self.get_or_create_label(label_name))

        if mark_read:
            remove_labels.append('UNREAD')

        if add_labels or remove_labels:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': add_labels,
                    'removeLabelIds': remove_labels
                }
            ).execute()
