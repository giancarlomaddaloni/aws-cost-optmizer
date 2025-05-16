# 💸 AWS Cost Optimizer — EBS Volume Cleanup Automation

**Automated multi-region cleanup system for unattached EBS volumes**, designed to reduce AWS storage costs through snapshotting, validation, email notifications, and timed deletion. Built and deployed using AWS CDK.

---

## 🧩 Features

- 📦 Scans all AWS regions for **available (unused) EBS volumes**
- 🔍 Validates lifecycle via **CloudTrail Detach/Attach events**
- 🪪 Creates **snapshots** for recovery before deletion
- ⏳ Tracks deletion eligibility in **DynamoDB**
- 📧 Sends **email warnings** via SES before deleting
- ⌛ Deletes volumes after expiration if unused
- 🛠️ Deployable using **CDK (TypeScript)**

---

## 🏗️ Architecture

1. **Lambda (Lister)**  
   Detects unused EBS volumes → stores snapshot and metadata in DynamoDB  
   → triggers SES warning

2. **Lambda (Killer)**  
   Validates volume inactivity and snapshot age → deletes volume if still unused

3. **DynamoDB**  
   Central state management of volume lifecycle, snapshot status, tags

4. **EventBridge**  
   Triggers both Lambdas every 24h for continuous cleanup

---

## 📁 Project Structure

```
aws-cost-optimizer/
├── cdk/
│   └── lib/
│       └── lambda-functions/
│           ├── volumeListing/
│           │   └── lambda_function_lister.py
│           └── volumeKiller/
│               └── lambda_function_killer.py
│       ├── lambda-volumeCleaner-stack.ts
│       ├── dynamoDB-stack.ts
│       └── lambda-uploader.ts
├── docs/
│   └── architecture-diagram.png (optional)
├── package.json
├── tsconfig.json
├── cdk.json
├── LICENSE
```

---

## 🚀 Deployment

1. Configure your AWS environment variables:
   - `ACCOUNT`
   - `REGION`
   - `TABLE_NAME`
   - `MAX_DAYS_PER_VOLUME`
   - `MAX_DAYS_PER_VOLUME_UNVALIDATED`
   - `MAX_DAYS_PER_VOLUME_NOTIFIED`

2. Deploy with CDK:

```bash
npm install
npx cdk bootstrap
npx cdk deploy
```

---

## 🔄 Lifecycle Summary

| Stage         | Condition                                                | Action                         |
|---------------|-----------------------------------------------------------|--------------------------------|
| 📡 Listing     | Volume in `available` state                               | Create snapshot + DB entry     |
| 🕓 Notified    | After X days (configurable), if still unused              | Send SES warning email         |
| ❌ Deletion    | Snapshot > age threshold + no new attachment via CloudTrail | Delete volume via Lambda       |

---

## 🧪 Testing & Pipeline

This project includes Jest test config (`jest.config.js`) and is compatible with GitLab/GitHub CI.  
You can adapt your pipeline to watch these files:

```
cdk/lib/lambda-functions/volumeListing/lambda_function_lister.py
cdk/lib/lambda-functions/volumeKiller/lambda_function_killer.py
```

Trigger your job with commit message:
```
git commit -m "deploy-volumeCleaner"
```

---

## 📬 Email Integration

Configured to send warning emails via **Amazon SES** from `kanu@example.com` before deleting volumes.  
Modify the SES sender and recipient in the `send_Email()` function in `lambda_function_lister.py`.

---

## 📜 License

MIT License. Use freely with attribution.

---

## 👥 Authors & Credits

- 👤 Giancarlo Maddaloni — DevOps Engineer  
- 🏢 Kanu Technologies — Secure & Efficient Cloud Automation

Contributions welcome via pull requests or issues.
