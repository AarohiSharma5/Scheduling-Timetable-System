# Pilot Operator Runbook

A plain-English guide for running this app for 1–2 schools, written for a
**non-technical operator**. No coding required — just clicking in dashboards and
occasionally copy-pasting a value.

If you can use Gmail settings, you can do everything here.

---

## Part 1 — One-time setup (about an hour)

You'll create accounts on two free/cheap services and connect them.

### Step 1: Put the code on GitHub
1. Create a free account at https://github.com.
2. Create a new **private** repository (e.g. `school-app`).
3. Upload this whole project folder to it (GitHub's website has an "upload files"
   button, or ask a tech-savvy friend to `git push` it once).

### Step 2: Create the app on Render
1. Sign up at https://render.com (you can log in with your GitHub account).
2. Click **New +  >  Blueprint**.
3. Choose your `school-app` repository. Render finds the `render.yaml` file and
   shows it will create: a **web service**, a **worker**, a **database**, and a
   **Redis** store. Click **Apply**.
4. Wait ~5–10 minutes for the first build. The web service gets a public address
   like `https://timetable-web.onrender.com` — **this is your school's URL.**

### Step 3: Fill in the remaining settings
Some values can't be auto-generated. In Render, open the **timetable-web**
service > **Environment**, and set:

| Setting | What to put | Notes |
|---|---|---|
| `APP_BASE_URL` | Your public URL (e.g. `https://timetable-web.onrender.com`) | Makes email links clickable |
| `PII_ENCRYPTION_KEY` | A key you generate (see below) | **Save a copy somewhere safe** |

To generate the encryption key, in Render open the web service > **Shell** tab and run:
```
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output into `PII_ENCRYPTION_KEY`.

> ⚠️ **Keep `PII_ENCRYPTION_KEY` backed up.** If you lose it, encrypted data
> (parent phone numbers, addresses) can never be read again.

Now open the **timetable-worker** service > **Environment** and copy three values
so they MATCH the web service exactly: `JWT_SECRET_KEY`, `SECRET_KEY`,
`PII_ENCRYPTION_KEY`. (Find them on the web service's Environment page.)

### Step 4: Turn on email (so invites/resets actually send)
Sign up for a free email-sending service — **Resend** (https://resend.com) is the
simplest. Get an SMTP username/password from them, then on **both** the web and
worker services set:

| Setting | Example |
|---|---|
| `SMTP_HOST` | `smtp.resend.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | (from Resend) |
| `SMTP_PASSWORD` | (from Resend) |
| `EMAIL_FROM` | `School App <noreply@yourdomain.com>` |

After saving, Render redeploys automatically. **Until you do this, invitation and
password-reset links won't be emailed** — but you can still read them from the
service **Logs** and hand them out manually (fine for day one).

### Step 5: Confirm it's alive
Visit `https://<your-url>/api/health/ready` in a browser. You want to see
`"status": "ready"`. If it says the database isn't ready, wait a minute and retry.

---

## Part 2 — Onboard a school (you do this for each pilot school)

1. Go to your app URL. Use the **"Create organization / school"** sign-up to make
   the school and its first admin account. (You can do this for the school, then
   hand them the admin login — or let the principal do it with you on a call.)
2. Log in as that school's admin.
3. Set up the basics in this order: **school timings/periods**, **subjects**,
   **classes (batches)**, **rooms**, then **teachers**.
4. **Bulk import** teachers/students if you have spreadsheets (look for the import
   option in the admin area) — much faster than typing.
5. Invite staff: use **Invite** with their email. They get an email with a link to
   set their own password. (No email yet? Copy the link from Render Logs.)
6. Generate the timetable from the **Timetable** tab. Use the **Pre-flight Check**
   first — it warns you about anything that won't fit before you generate.

> Each school's data is fully separate. One school can never see another's.

---

## Part 3 — Everyday operations (a few minutes a week)

### Reset someone's password
- Tell them to use **"Forgot password"** on the login page — they'll get an email.
- No email set up yet? Ask them to trigger it, then copy the reset link from the
  web service **Logs** in Render and send it to them.

### See if something is wrong
- Render dashboard shows each service as **green (healthy)** or not.
- Click a service > **Logs** to see what's happening / any errors.
- Health checks: `/api/health/live` (is it up?) and `/api/health/ready` (is the
  database connected?).

### Backups (your safety net)
- Render's database has **automatic daily backups** — you don't have to do
  anything. To restore, use Render's database **Backups / Recovery** tab.
- Extra-safe manual backup any time (from a computer with the project + Docker):
  ```
  ./scripts/backup_db.sh
  ```
  Test that a backup actually restores **before** you rely on it.

### Updating the app later
- Push new code to GitHub. Render rebuilds and redeploys automatically, running
  database updates (`flask db upgrade`) for you before going live.

---

## Part 4 — What to tell your pilot schools (set expectations)

- It's an **early pilot**: report bugs, expect occasional rough edges.
- Their data is private and backed up daily.
- Support = you. Agree on how they reach you (a WhatsApp group / email).
- Keep the pilot to **1–2 schools** until you've seen a full term run smoothly.

---

## Part 5 — Before going beyond a pilot (hand this list to an engineer)

These are deferred for a small pilot but needed to grow:
- Uptime/error alerting (e.g. Sentry, Render alerts, an uptime monitor).
- Off-site backup copies + a tested restore drill.
- Load testing for many schools at peak (Monday 8am).
- A guided setup wizard + friendlier error messages for self-serve onboarding.
- Database high-availability (standby replica).

---

## Quick reference

| I want to… | Where |
|---|---|
| See if the app is up | Render dashboard (green) or `/api/health/ready` |
| Read errors | Render > service > Logs |
| Add a school | App sign-up page |
| Invite staff | App admin > Invite |
| Reset a password | App login > Forgot password |
| Restore data | Render > database > Backups |
| Change a setting/secret | Render > service > Environment |
