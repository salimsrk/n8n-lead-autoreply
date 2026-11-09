# AI Lead Auto-Reply & Qualifier (n8n)

An n8n automation that **replies to every new customer enquiry within seconds**, sorts leads into hot, warm and cold with AI, saves each one to Google Sheets, and alerts the owner on Telegram when a buyer is ready to buy.

**Problem it solves:** small businesses lose customers because nobody replies to website or Instagram enquiries for hours. This workflow replies right away and makes sure hot leads get a call first.

## Flow

```
Website / form / ad lead
        │  POST /webhook/new-lead
        ▼
 Normalize Lead ──▶ AI Classify + Draft Reply (Gemini) ──▶ Parse AI Result
 (clean phone,       intent · priority · product ·          (safe JSON parsing,
  validate)          reply in customer's language            fallback reply if AI fails)
                                                                   │
                                     ┌─────────────────────────────┴───────────┐
                                     ▼                                         ▼
                           Save to Google Sheet                         Is Hot Lead?
                                     │                                         │ yes
                                     ▼                                         ▼
                        Reply to Customer (JSON)                  Alert Owner (Telegram 🔥)
```

## Features

- Instant AI reply in **English, Tamil or Tanglish**, matching the customer
- Lead scoring: `hot` (ready to buy) / `warm` / `cold`, plus intent and product detection
- **Never breaks:** if the AI call fails or returns bad JSON, the customer still gets a polite default reply and the lead is still saved
- Input validation: rejects leads with no message or no contact details
- Every lead logged in Google Sheets for follow-up

## Setup (10 minutes)

1. Import `workflow.json` into n8n (**Workflows → Import from file**)
2. Create the credentials:
   - **Gemini:** Header Auth credential, name `x-goog-api-key`, value = your key from Google AI Studio
   - **Google Sheets:** OAuth2. Make a sheet with a tab called `Leads`, then paste its URL into the *Save to Google Sheet* node
   - **Telegram:** create a bot with @BotFather and put your chat ID in the *Alert Owner* node
3. Activate the workflow and send a test lead:

```bash
curl -X POST https://YOUR-N8N/webhook/new-lead \
  -H "Content-Type: application/json" \
  -d '{"name":"Ravi","phone":"+91 98765 43210","message":"150Ah battery price enna? Indru install panna mudiyuma?"}'
```

Sample response:

```json
{ "ok": true, "priority": "hot", "reply": "Hi Ravi! 150Ah tubular battery Rs.12,800. Indru evening install pannalaam, confirm panna intha number-ku call pannunga 😊" }
```

## Tests

The JavaScript inside the Code nodes is tested with mocked n8n inputs:

```bash
node tests/code_nodes.test.js
```

`build_workflow.py` regenerates `workflow.json`, so the JS stays readable and version-controlled.

## Swap-ins for clients

- Telegram → **WhatsApp Business Cloud API** node, so the reply goes straight to the customer's WhatsApp
- Webhook → Facebook/Instagram Lead Ads, Google Forms, IndiaMART or JustDial lead emails
- Google Sheets → HubSpot, Zoho CRM or Airtable

---
Built by Salim, data engineer and AI automation developer.
