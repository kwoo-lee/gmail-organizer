// ==================== 상수 ====================
const RULES_KEY = 'GMAIL_RULES';
const LAST_CHECK_KEY = 'LAST_CHECK_TIME';


// ==================== 메인 실행 ====================
function main() {
  const rules = getRules();
  if (!rules || rules.length === 0) {
    Logger.log('규칙이 없습니다. initializeRules()를 먼저 실행해주세요.');
    return;
  }

  const lastCheckTime = getLastCheckTime();
  const now = new Date();

  const query = `in:inbox after:${Math.floor(lastCheckTime.getTime() / 1000)}`;
  const threads = GmailApp.search(query);

  let processedCount = 0;
  for (const thread of threads) {
    for (const message of thread.getMessages()) {
      if (message.getDate() > lastCheckTime) {
        processMessage(message, thread, rules);
        processedCount++;
      }
    }
  }

  if (processedCount > 0) {
    Logger.log(`${processedCount}개 메시지 처리 완료`);
  }

  PropertiesService.getScriptProperties().setProperty(LAST_CHECK_KEY, now.toISOString());
}


// ==================== 메시지 처리 ====================
function processMessage(message, thread, rules) {
  const email = {
    from: message.getFrom(),
    subject: message.getSubject(),
  };

  const matchedRules = matchRules(email, rules);
  if (matchedRules.length === 0) return;

  for (const rule of matchedRules) {
    const actions = rule.actions || {};

    if (actions.trash) {
      thread.moveToTrash();
      Logger.log(`[TRASH] 규칙: '${rule.name}' | 발신: ${email.from} | 제목: ${email.subject}`);
      return; // 삭제된 메일은 이후 규칙 적용 불필요
    }
    if (actions.label) {
      thread.addLabel(getOrCreateLabel(actions.label));
    }
    if (actions.mark_read) {
      message.markRead();
    }

    Logger.log(`[PROCESSED] 규칙: '${rule.name}' | 라벨: ${actions.label || '-'} | 읽음: ${actions.mark_read || false} | 발신: ${email.from} | 제목: ${email.subject}`);
  }
}


// ==================== 규칙 엔진 ====================
function matchRules(email, rules) {
  return rules.filter(rule => checkRule(rule, email));
}

function checkRule(rule, email) {
  const conditions = rule.conditions || {};
  const matchType = rule.match || 'any';
  const results = [];

  if (conditions.sender && conditions.sender.length > 0) {
    const senderLower = email.from.toLowerCase();
    results.push(conditions.sender.some(s => senderLower.includes(s.toLowerCase())));
  }

  if (conditions.keywords && conditions.keywords.length > 0) {
    const subjectLower = email.subject.toLowerCase();
    results.push(conditions.keywords.some(kw => subjectLower.includes(kw.toLowerCase())));
  }

  if (results.length === 0) return false;
  return matchType === 'all' ? results.every(Boolean) : results.some(Boolean);
}


// ==================== 라벨 관리 ====================
function getOrCreateLabel(name) {
  const label = GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
  return label;
}


// ==================== 규칙 관리 ====================
function getRules() {
  const json = PropertiesService.getScriptProperties().getProperty(RULES_KEY);
  if (!json) return [];
  return JSON.parse(json);
}

// 규칙을 업데이트할 때 이 함수의 jsonString을 수정하고 실행하세요
function setRules() {
  const jsonString = JSON.stringify([
    {
      "name": "ADV 광고 삭제",
      "conditions": {
        "keywords": ["ADV"]
      },
      "match": "any",
      "actions": {
        "trash": true
      }
    },
    {
      "name": "DBS 은행알림",
      "conditions": {
        "sender": ["ibanking.alert@dbs.com"]
      },
      "match": "any",
      "actions": {
        "label": "Singapore/Banks/DBS",
        "mark_read": true
      }
    },
    {
      "name": "GXS 은행알림",
      "conditions": {
        "sender": ["no-reply@gxs.com.sg"]
      },
      "match": "any",
      "actions": {
        "label": "Singapore/Banks/GXS",
        "mark_read": true
      }
    },
    {
      "name": "Citi 은행알림",
      "conditions": {
        "sender": ["alerts@citibank.com.sg"]
      },
      "match": "any",
      "actions": {
        "label": "Singapore/Banks/Citi",
        "mark_read": true
      }
    },
    {
      "name": "SC 은행알림",
      "conditions": {
        "sender": ["OnlineBanking.SG@sc.com"]
      },
      "match": "any",
      "actions": {
        "label": "Singapore/Banks/SC",
        "mark_read": true
      }
    },
    {
      "name": "쇼핑",
      "conditions": {
        "sender": [
          "noreply@support.lazada.sg",
          "noreply@ninjavan.co",
          "no-reply@jtexpress.sg",
          "no-reply@fairprice.com.sg",
          "no-reply@lockeralliance.net"
        ]
      },
      "match": "any",
      "actions": {
        "label": "Shopping",
        "mark_read": true
      }
    }
  ], null, 2);

  PropertiesService.getScriptProperties().setProperty(RULES_KEY, jsonString);
  Logger.log('규칙 저장 완료:\n' + jsonString);
}

function printRules() {
  const json = PropertiesService.getScriptProperties().getProperty(RULES_KEY);
  Logger.log(json || '저장된 규칙이 없습니다.');
}


// ==================== 트리거 설정 ====================
function createTrigger() {
  // 기존 main 트리거 삭제 후 재생성
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'main')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('main')
    .timeBased()
    .everyMinutes(1)
    .create();

  Logger.log('트리거 생성 완료: main() 1분마다 실행');
}

function deleteTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'main')
    .forEach(t => ScriptApp.deleteTrigger(t));

  Logger.log('트리거 삭제 완료');
}


// ==================== 시간 관리 ====================
function getLastCheckTime() {
  const stored = PropertiesService.getScriptProperties().getProperty(LAST_CHECK_KEY);
  if (stored) return new Date(stored);

  // 첫 실행 시 1분 전부터 탐색
  const oneMinuteAgo = new Date();
  oneMinuteAgo.setMinutes(oneMinuteAgo.getMinutes() - 1);
  return oneMinuteAgo;
}
