# BrisAI — How to Deploy (Railway + Custom Domain)

## What you have

```
brisnet_app/
├── app.py                 ← Flask backend
├── brisnet_fields.py      ← Field index map
├── brisnet_parser.py      ← CSV parser
├── requirements.txt
└── templates/
    └── index.html         ← Frontend
```

---

## Step 1 — Airtable setup (10 min)

Go to https://airtable.com and create a new Base called **BrisAI Trial**.

**Table 1: Prospects**
Create these fields:
- Name (Single line text)
- Email (Email)
- Company (Single line text)
- First Access (Date)
- Trial Days (Number)
- Status (Single line text)

**Table 2: Usage**
Create these fields:
- Email (Single line text)
- Name (Single line text)
- Company (Single line text)
- File (Single line text)
- Track (Single line text)
- Race (Single line text)
- Race Date (Single line text)
- Class (Single line text)
- Purse (Single line text)
- Analyzed At (Single line text)

**Get your Airtable credentials:**

1. Go to https://airtable.com/create/tokens → Create new token
   - Name it: BrisAI
   - Scopes: data.records:read + data.records:write
   - Access: your BrisAI Trial base
   - Copy the token — it starts with `pat...`

2. Get your Base ID:
   - Open your BrisAI Trial base
   - Go to Help → API Documentation
   - The URL looks like: https://airtable.com/appXXXXXXXXXXXX/...
   - That appXXXXXXXXXXXX is your Base ID — copy it

---

## Step 2 — Put the files on GitHub (5 min)

Railway deploys from GitHub. You need a free account.

1. Go to https://github.com → New Repository → name it `brisai`
2. Unzip the `brisnet_app.zip` file you downloaded
3. Upload all the files inside the `brisnet_app` folder (not the folder itself):
   - Click "uploading an existing file"
   - Drag in: app.py, brisnet_fields.py, brisnet_parser.py, requirements.txt
   - Then drag in the `templates` folder
4. Click Commit changes

---

## Step 3 — Deploy to Railway (5 min)

1. Go to https://railway.app → Log in with GitHub
2. Click New Project → Deploy from GitHub repo → select `brisai`
3. Railway will detect Python automatically and start deploying

**Add your environment variables** — in Railway dashboard → your project → Variables → Add:

| Variable | Value |
|----------|-------|
| ANTHROPIC_API_KEY | sk-ant-... |
| AIRTABLE_PAT | pat... |
| AIRTABLE_BASE_ID | appXXXXXXXX |
| SECRET_KEY | any long random phrase (e.g. "horseswin2024moonlight") |
| TRIAL_DAYS | 3 |

Click Deploy. Railway gives you a URL like `brisai-production.up.railway.app`.

---

## Step 4 — Connect your domain (10 min)

**In Railway:**
1. Go to your project → Settings → Networking → Custom Domain
2. Type your domain (e.g. `app.yourdomain.com` or just `yourdomain.com`)
3. Railway shows you a CNAME record to add — copy it

**In Cheapnames:**
1. Log in → My Domains → your domain → DNS Management
2. Add a CNAME record:
   - Host/Name: `app` (or `@` for the root domain)
   - Points to: the value Railway gave you
   - TTL: 3600 (or default)
3. Save

DNS takes 5–30 minutes to propagate. Then your app is live at your domain.

---

## How the trial gate works

- Each prospect enters their email on first visit → logged with today's date
- On return visits with the same email, the app checks how many days have passed
- After 3 days: locked screen appears with "contact us to continue"
- You can extend anyone's trial by changing their **First Access** date in Airtable
- Change the trial length anytime via the `TRIAL_DAYS` environment variable in Railway

---

## How to extend a prospect's trial

1. Open Airtable → BrisAI Trial → Prospects
2. Find the prospect's row
3. Change their **First Access** date to today
4. That gives them another 3 days from now

---

## Update the contact email in the expired screen

In `templates/index.html`, find this line and replace with your email:
```html
<a href="mailto:hello@yourdomain.com">Contact us to continue →</a>
```

---

## Checking usage

Open Airtable → Usage table to see:
- Who is using it and how often
- Which tracks and races they're analyzing
- Timestamps for each analysis

