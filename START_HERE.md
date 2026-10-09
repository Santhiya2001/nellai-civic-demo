# Your ME project demo

**Using the ZIP on a different PC? Start with [RUN_ON_ANOTHER_PC.md](RUN_ON_ANOTHER_PC.md).**
It includes Windows, Linux and macOS launchers and the private Gmail setup steps.

## 1. Open the folder

In VS Code: **File → Open Folder → `/home/santhiya/nellai-build/nellai-green-civic`**.

## 2. Start the application

Open the VS Code terminal and run:

```bash
bash start.sh
```

Then visit **http://localhost:8080**.

If it says the demo is already running, simply open that address. To stop it, run `bash stop.sh` or press Ctrl+C in its terminal.

## 3. Sign in

Open **[runtime/DEMO_CREDENTIALS.md](runtime/DEMO_CREDENTIALS.md)** privately. It contains separately generated logins for the citizen, authority and administrator.

## 4. Open your presentation

**[presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx](presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx)**

There are 23 slides, editable diagrams and tables, fresh application screenshots, and speaker notes. The cover includes Santhiya M, register number 952825405014, M.E. CSE — Final Year, and the supplied SCAD College of Engineering & Technology logo. A PDF viewing copy is in the same folder. The earlier presentation remains in `presentation/`.

## 5. Practise the demonstration

Follow **[docs/demo-guide.md](docs/demo-guide.md)**: citizen reports → admin checks the email outbox → authority resolves → citizen verifies. The guide includes a sample complaint, a speaking script and viva answers.

**Email demonstration:** sign in as administrator and choose **Authority email outbox**.
Recipient: `sandymuthukutti@gmail.com`. Complaint `NGC-063524AD` is the prepared test.
On the original PC, Gmail accepted this test email and the worker has automatic
sending enabled. `SENT` means mail-server acceptance; check Inbox/Spam to confirm
arrival. A newly extracted copy needs its own private email setup, as explained
in [RUN_ON_ANOTHER_PC.md](RUN_ON_ANOTHER_PC.md). Its database contains fresh demo data.

This is a simple local web demo. Play Store/native mobile work is deferred. The AI service is a disabled extension interface, not a trained classifier. All sample records are labelled as demo data.

Full setup and development instructions: **[README.md](README.md)**.
