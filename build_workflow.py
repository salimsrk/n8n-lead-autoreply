"""Builds workflow.json (keeps the JS readable here instead of escaped inside JSON)."""
import json

NORMALIZE_JS = r"""
// Normalize incoming lead from any form (website, Google Form, Facebook lead ad via Zapier, etc.)
const b = $input.first().json.body ?? $input.first().json;
const clean = (v) => (v ?? '').toString().trim();
const lead = {
  name: clean(b.name) || 'Customer',
  phone: clean(b.phone).replace(/[^\d+]/g, ''),
  email: clean(b.email).toLowerCase(),
  message: clean(b.message),
  source: clean(b.source) || 'website',
  received_at: new Date().toISOString(),
};
if (!lead.message) throw new Error('Lead has no message');
if (!lead.phone && !lead.email) throw new Error('Lead needs a phone or email');
return [{ json: lead }];
""".strip()

PARSE_JS = r"""
// Parse Gemini's JSON reply safely; fall back to a polite default if the AI output is broken
const lead = $('Normalize Lead').first().json;
let ai = {};
try {
  const text = $input.first().json.candidates[0].content.parts[0].text;
  ai = JSON.parse(text.replace(/```json|```/g, '').trim());
} catch (e) {
  ai = {};
}
const allowed = ['hot', 'warm', 'cold'];
const priority = allowed.includes(ai.priority) ? ai.priority : 'warm';
return [{
  json: {
    ...lead,
    intent: ai.intent || 'general_enquiry',
    priority,
    product: ai.product || '',
    reply: ai.reply || `Hi ${lead.name}, thanks for contacting us! Our team will call you shortly.`,
    ai_ok: Boolean(ai.reply),
  },
}];
""".strip()

PROMPT = (
    "You are a sales assistant for a small business. Classify this customer enquiry and draft a short, "
    "friendly reply (max 60 words) in the same language as the customer (English, Tamil or Tanglish). "
    "Return JSON only with keys: intent (price_enquiry | service_request | complaint | general_enquiry), "
    "priority (hot = ready to buy now, warm = interested, cold = just browsing), product, reply."
)

GEMINI_BODY = (
    '={{ JSON.stringify({ contents: [{ parts: [{ text: '
    + json.dumps(PROMPT)
    + ' + "\\n\\nCustomer name: " + $json.name + "\\nMessage: " + $json.message }] }], '
    'generationConfig: { responseMimeType: "application/json" } }) }}'
)

nodes = [
    {"id": "1", "name": "New Lead (Webhook)", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
     "position": [0, 300], "webhookId": "lead-autoreply",
     "parameters": {"httpMethod": "POST", "path": "new-lead", "responseMode": "responseNode", "options": {}}},
    {"id": "2", "name": "Normalize Lead", "type": "n8n-nodes-base.code", "typeVersion": 2,
     "position": [220, 300], "parameters": {"jsCode": NORMALIZE_JS}},
    {"id": "3", "name": "AI Classify + Draft Reply", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [440, 300],
     "parameters": {
         "method": "POST",
         "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
         "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
         "sendBody": True, "specifyBody": "json", "jsonBody": GEMINI_BODY, "options": {"timeout": 30000}},
     "credentials": {"httpHeaderAuth": {"id": "", "name": "Gemini API Key (x-goog-api-key)"}},
     "onError": "continueRegularOutput"},
    {"id": "4", "name": "Parse AI Result", "type": "n8n-nodes-base.code", "typeVersion": 2,
     "position": [660, 300], "parameters": {"jsCode": PARSE_JS}},
    {"id": "5", "name": "Save to Google Sheet", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5,
     "position": [880, 200],
     "parameters": {"operation": "append",
                    "documentId": {"__rl": True, "mode": "url", "value": "PASTE_YOUR_GOOGLE_SHEET_URL"},
                    "sheetName": {"__rl": True, "mode": "name", "value": "Leads"},
                    "columns": {"mappingMode": "autoMapInputData", "value": {}}, "options": {}},
     "credentials": {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets account"}}},
    {"id": "6", "name": "Is Hot Lead?", "type": "n8n-nodes-base.if", "typeVersion": 2,
     "position": [880, 420],
     "parameters": {"conditions": {
         "options": {"caseSensitive": True, "typeValidation": "strict"}, "combinator": "and",
         "conditions": [{"id": "c1", "leftValue": "={{ $json.priority }}", "rightValue": "hot",
                         "operator": {"type": "string", "operation": "equals"}}]}, "options": {}}},
    {"id": "7", "name": "Alert Owner (Telegram)", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
     "position": [1100, 400],
     "parameters": {"chatId": "PASTE_YOUR_TELEGRAM_CHAT_ID",
                    "text": "=🔥 HOT LEAD\nName: {{ $json.name }}\nPhone: {{ $json.phone }}\n"
                            "Wants: {{ $json.product || $json.intent }}\nMessage: {{ $json.message }}",
                    "additionalFields": {}},
     "credentials": {"telegramApi": {"id": "", "name": "Telegram bot"}}},
    {"id": "8", "name": "Reply to Customer", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
     "position": [1100, 200],
     "parameters": {"respondWith": "json",
                    "responseBody": "={{ { ok: true, reply: $('Parse AI Result').first().json.reply, "
                                    "priority: $('Parse AI Result').first().json.priority } }}",
                    "options": {}}},
]

connections = {
    "New Lead (Webhook)": {"main": [[{"node": "Normalize Lead", "type": "main", "index": 0}]]},
    "Normalize Lead": {"main": [[{"node": "AI Classify + Draft Reply", "type": "main", "index": 0}]]},
    "AI Classify + Draft Reply": {"main": [[{"node": "Parse AI Result", "type": "main", "index": 0}]]},
    "Parse AI Result": {"main": [[{"node": "Save to Google Sheet", "type": "main", "index": 0},
                                  {"node": "Is Hot Lead?", "type": "main", "index": 0}]]},
    "Save to Google Sheet": {"main": [[{"node": "Reply to Customer", "type": "main", "index": 0}]]},
    "Is Hot Lead?": {"main": [[{"node": "Alert Owner (Telegram)", "type": "main", "index": 0}], []]},
}

wf = {"name": "AI Lead Auto-Reply & Qualifier", "nodes": nodes, "connections": connections,
      "settings": {"executionOrder": "v1"}, "pinData": {}, "active": False}

with open("workflow.json", "w") as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
print("workflow.json written:", len(nodes), "nodes")
