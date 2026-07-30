# Note-Cloud — Deployment Guide
## AWS Elastic Beanstalk + Route 53 + HTTPS

### What you'll end up with
```
note-cloud.com  (Route 53)
      │
      ▼
 CloudFront / ALB  ← ACM SSL cert (free, auto-renews)
      │  HTTPS
      ▼
Elastic Beanstalk (Python, gunicorn)
      │
      ▼
SQLite at /var/app/scrib_d.db  (survives redeploys)
```

---

## Prerequisites

Install these on your Mac once:

```bash
# AWS CLI
brew install awscli

# EB CLI
pip install awsebcli --upgrade

# Verify
aws --version
eb --version
```

Then configure your AWS credentials:

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region:        us-east-1   (or wherever you want to host)
# Default output format: json
```

> Get your access key from AWS Console → IAM → Users → your user → Security credentials → Create access key.

---

## Step 1 — Request an SSL Certificate (ACM)

Do this **first** because DNS validation can take a few minutes.

1. Go to **AWS Certificate Manager** → make sure you're in **us-east-1** (required for EB/ALB)
2. Click **Request a certificate** → **Request a public certificate**
3. Add these domain names:
   - `note-cloud.com`
   - `www.note-cloud.com`
4. Validation method: **DNS validation**
5. Click **Request**
6. Open the certificate → click **Create records in Route 53** (one-click since your domain is already there)
7. Wait ~2 minutes until status shows **Issued** — keep this tab open, you'll need the ARN later

---

## Step 2 — Prepare the deployment package

From your `scribd/` folder, create the zip. Run this in Terminal:

```bash
cd ~/Desktop/scribd

zip -r notecloud.zip \
  app.py \
  Procfile \
  requirements.txt \
  templates/ \
  static/
```

**Do NOT include:** `.env`, `venv/`, `scrib_d.db`, `*.zip`, `__pycache__/`

---

## Step 3 — Create the Elastic Beanstalk application

### In the AWS Console

1. Go to **Elastic Beanstalk** → **Create application**
2. **Application name**: `note-cloud`
3. Click **Create**

### Create the environment

1. Inside your new application → **Create environment**
2. Settings:
   - **Environment tier**: Web server environment
   - **Environment name**: `note-cloud-prod`
   - **Platform**: Python
   - **Platform branch**: Python 3.11 (or latest available)
   - **Application code**: Upload your zip → choose `notecloud.zip`
3. Click **Configure more options** (important — don't skip)

### Under "Capacity"
- Change preset to **Load balanced**
- Min instances: `1`, Max instances: `1` (scale up later if needed)
- Instance type: `t3.micro` (free-tier eligible)

### Under "Load balancer"
- Type: **Application Load Balancer**
- Add a listener:
  - Port: `443`, Protocol: `HTTPS`
  - SSL certificate: choose `note-cloud.com` (the cert you just created)
- Keep the default port 80 HTTP listener (you'll redirect it to HTTPS shortly)

4. Click **Create environment** and wait ~5 minutes for the green health check

---

## Step 4 — Set environment variables

In your EB environment → **Configuration** → **Updates, monitoring, and logging** → **Edit** under "Environment properties":

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `SECRET_KEY` | a long random string (run `python3 -c "import secrets; print(secrets.token_hex(32))"` to generate one) |
| `OWNER_CODE` | your owner unlock code |
| `DB_PATH` | `/var/app/scrib_d.db` |
| `FLASK_ENV` | `production` |
| `GOOGLE_CLIENT_ID` | from Google Cloud Console (see below) |
| `GOOGLE_CLIENT_SECRET` | from Google Cloud Console (see below) |
| `GOOGLE_REDIRECT_URI` | `https://note-cloud.com/google/callback` |
| `GOOGLE_LOGIN_REDIRECT_URI` | `https://note-cloud.com/auth/google/callback` |
| `STRIPE_SECRET_KEY` | from dashboard.stripe.com (see below) |
| `STRIPE_WEBHOOK_SECRET` | from the webhook endpoint you create (see below) |
| `STRIPE_PRICE_STUDENT_MONTHLY` / `_ANNUAL` | the Price IDs for the Student plan |
| `STRIPE_PRICE_PRO_MONTHLY` / `_ANNUAL` | the Price IDs for the Pro plan |
| `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` | from your Notion public integration (see below) |
| `NOTION_REDIRECT_URI` | `https://note-cloud.com/notion/callback` |
| `APPLE_CLIENT_ID` / `APPLE_TEAM_ID` / `APPLE_KEY_ID` / `APPLE_PRIVATE_KEY` | from your Apple Developer account (see below) |
| `APPLE_REDIRECT_URI` | `https://note-cloud.com/auth/apple/callback` |

Click **Apply** and wait for the environment to update.

> `FLASK_ENV=production` enables secure session cookies (HTTPS-only). Do not skip this.
>
> **Google OAuth (Docs export + "Continue with Google"):** the `.env` file only has the
> localhost redirect URIs, which only work for local dev. Before this works in prod:
> 1. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → your
>    OAuth 2.0 Client ID → **Authorized redirect URIs**, add both prod URLs above
>    (in addition to, not instead of, the localhost ones — keep those for local dev).
> 2. Set the two `GOOGLE_REDIRECT_URI` / `GOOGLE_LOGIN_REDIRECT_URI` env vars above on EB.
> 3. If the OAuth consent screen is still in "Testing" mode, either publish it or add
>    your test users' emails under **OAuth consent screen → Test users**, or real users
>    will get an "access blocked" error.
>
> **Stripe (payments):**
> 1. Create the 4 recurring Prices (Student/Pro × monthly/annual) in the Stripe Dashboard
>    → Product catalog, and copy each Price ID into the env vars above.
> 2. Dashboard → Developers → Webhooks → **Add endpoint**, URL
>    `https://note-cloud.com/stripe/webhook`, and subscribe to `checkout.session.completed`,
>    `customer.subscription.updated`, and `customer.subscription.deleted`. Copy the signing
>    secret it gives you into `STRIPE_WEBHOOK_SECRET`.
> 3. Start in Stripe **test mode** end-to-end (test card `4242 4242 4242 4242`) before
>    switching the secret key to a live one.
>
> **Notion export:** create a **public** integration (not internal) at
> [notion.so/my-integrations](https://www.notion.so/my-integrations), set its redirect URI
> to the prod URL above, and copy the OAuth client ID/secret into the env vars. Each user
> connects their own workspace and picks which pages to share with Note-Cloud during that
> flow — nothing else is needed server-side.
>
> **Apple Sign-In:** requires a paid Apple Developer account. In the Apple Developer
> portal: register a Services ID (this is `APPLE_CLIENT_ID`, e.g. `com.note-cloud.web`)
> with "Sign in with Apple" enabled and the prod redirect URI above configured, note your
> Team ID (`APPLE_TEAM_ID`), then create a "Sign in with Apple" key — its Key ID is
> `APPLE_KEY_ID` and the downloaded `.p8` file's contents are `APPLE_PRIVATE_KEY`.

---

## Step 5 — Redirect HTTP → HTTPS

Create a file `.ebextensions/https-redirect.config` inside your project (not the zip, in the folder):

```bash
mkdir -p ~/Desktop/scribd/.ebextensions
```

Create `~/Desktop/scribd/.ebextensions/https-redirect.config` with this content:

```yaml
option_settings:
  aws:elasticbeanstalk:environment:proxy:
    ProxyServer: nginx

files:
  "/etc/nginx/conf.d/https_redirect.conf":
    mode: "000644"
    owner: root
    group: root
    content: |
      server {
        listen 80;
        return 301 https://$host$request_uri;
      }
```

Then rebuild your zip (add `.ebextensions/` to it) and redeploy by uploading via EB Console → **Upload and deploy**.

---

## Step 6 — Point note-cloud.com to Elastic Beanstalk

Since you bought the domain via Route 53, a hosted zone already exists.

1. Go to **Route 53** → **Hosted zones** → click `note-cloud.com`
2. You'll see NS and SOA records already there — leave those alone

### Root domain (note-cloud.com)

1. Click **Create record**
2. Record name: *(leave blank)*
3. Record type: **A**
4. Toggle **Alias** ON
5. Route traffic to: **Alias to Elastic Beanstalk environment**
6. Region: your region (e.g. `us-east-1`)
7. Environment: select your `note-cloud-prod` environment
8. Click **Create records**

### www subdomain (www.note-cloud.com)

1. Click **Create record**
2. Record name: `www`
3. Record type: **CNAME**
4. Value: your EB environment URL (e.g. `note-cloud-prod.us-east-1.elasticbeanstalk.com`)
5. TTL: `300`
6. Click **Create records**

> DNS on Route 53 propagates within 1–2 minutes (it's faster than most registrars).

---

## Step 7 — Verify

```bash
# Check DNS resolved
dig note-cloud.com +short
dig www.note-cloud.com +short

# Check HTTPS works (should return 200)
curl -I https://note-cloud.com
```

- Visit `https://note-cloud.com` in your browser — you should see the login page
- Visit `http://note-cloud.com` — should redirect to HTTPS automatically
- Check EB Console: environment health should be **Ok (green)**

---

## Step 8 — Important caveat: avatars

Profile photo uploads go to `static/avatars/` on the instance disk. These **will be lost** if AWS ever replaces the instance (e.g. during instance maintenance or scaling).

For now this is acceptable for a launch. When you're ready to fix it:
- Create an S3 bucket
- Change `upload_avatar()` in `app.py` to upload to S3 instead of local disk
- Serve avatar URLs directly from S3

---

## Ongoing: how to redeploy

After making code changes:

```bash
cd ~/Desktop/scribd

zip -r notecloud.zip \
  app.py \
  Procfile \
  requirements.txt \
  templates/ \
  static/ \
  .ebextensions/

# Then in EB Console: Upload and deploy → choose notecloud.zip
```

Or using the EB CLI (faster):

```bash
cd ~/Desktop/scribd

# First time only — run once
eb init note-cloud --region us-east-1 --platform python-3.11

# Every deploy after that
eb deploy note-cloud-prod
```

---

## Cost estimate

| Resource | Monthly cost |
|----------|-------------|
| t3.micro EC2 instance | ~$8–10 (or free if within free tier year) |
| Application Load Balancer | ~$16–18 |
| Route 53 hosted zone | $0.50 |
| ACM certificate | Free |
| **Total** | **~$25–29/mo** |

The ALB is the main cost. Once you have real users you can look at migrating to RDS (for a proper database) at which point you'd already be generating revenue to cover it.
