# Run Nellai Green & Civic on another PC

Extract the entire ZIP first. Keep all files together inside `Nellai_Green_Civic`.
Do not run the program from inside the ZIP preview or while it is still syncing.

## What you need

- **64-bit Python 3.12**, with pip and venv, and a recent web browser.
- Windows 10/11 on x64, a current Linux distribution, or macOS (Intel: 14 or
  later; Apple Silicon: 11 or later). Intel Macs use a compatible pinned Argon2
  binding so setup does not require compiling it.
- Internet for the first setup to download the pinned Python packages.
- Internet whenever sending Gmail alerts or loading the external basemap.
- Node.js, Docker and PostgreSQL are **not required for this portable demo**.
  The compiled website is included and the launcher creates a local SQLite database.

Use an official Python installer: https://www.python.org/downloads/ . Windows and
macOS installer files are also listed on the
[Python 3.12.10 release page](https://www.python.org/downloads/release/python-31210/).
Choose the
Python **3.12** series, not a different default version. On Windows select **Add
python.exe to PATH** and keep the Python launcher and pip selected. On Ubuntu
24.04, `sudo apt install python3.12 python3.12-venv` provides the needed interpreter
and venv module. On macOS use the Python 3.12 universal installer and run its
`Install Certificates.command` if package downloads report certificate errors
([Python's macOS setup guide](https://docs.python.org/3.12/using/mac.html)).
Other Linux distributions need their equivalent Python 3.12 and venv packages.

## Windows

1. Extract the folder somewhere writable, such as Documents.
2. Double-click **START_WINDOWS.bat**.
3. First setup installs dependencies, applies migrations and creates labelled demo data.
4. When the terminal shows READY, open **http://localhost:8080**.

## Linux

Open a terminal in the extracted folder and run:

```bash
bash START_LINUX.sh
```

## macOS

Open Terminal, change into the extracted folder, then run:

```bash
bash START_MAC.command
```

The same URL, **http://localhost:8080**, is used on all three platforms. Keep the
terminal open while presenting. Press **Ctrl+C** to stop; records remain saved.
To run again, use the same launcher. Repeated setup preserves existing records
and passwords. Stop the first instance before starting a second.

## Sign in and present

Open `runtime/DEMO_CREDENTIALS.md` privately after first setup. The generated
passwords are different on each installation. The three accounts are:

| Role | Email | Demo action |
|---|---|---|
| Citizen | citizen@nellai.example | Submit and verify a complaint |
| Authority | authority@nellai.example | Acknowledge, work and resolve |
| Administrator | admin@nellai.example | View email outbox and responsibility settings |

Presentation: `presentation/demo-ready/Nellai_Green_Civic_Demo_Ready.pptx`.
Viewing backup: the PDF beside it. Speaking script, sample complaint and viva
answers: **docs/demo-guide.md**. Example upload: `tests/fixtures/evidence.png`.

## Enable Gmail on the new PC

Your Gmail password, old login passwords and current database are deliberately
excluded from the ZIP. A new installation starts with email sending disconnected,
but new complaints queue alerts for **sandymuthukutti@gmail.com**.

1. Stop the demo with Ctrl+C.
2. Create a Google App Password for the sending Gmail account at
   https://myaccount.google.com/apppasswords . This requires 2-Step Verification;
   see https://support.google.com/accounts/answer/185833 .
3. Open a terminal in the extracted folder and run the appropriate command:

| Platform | Command |
|---|---|
| Windows Command Prompt | `START_WINDOWS.bat --email` |
| Linux | `bash START_LINUX.sh --email` |
| macOS | `bash START_MAC.command --email` |

4. At Step 1 press Enter for the recipient. At Step 2 press Enter if sending from
   the same Gmail account, or enter the account that generated your App Password.
   At Step 3 paste the App Password into the hidden prompt and press Enter.
5. Restart with the ordinary launcher. Submit one clearly labelled test complaint.
6. Open **Administrator → Authority email outbox** and allow about 30 seconds.
   `SENT` means the mail server accepted the message. Confirm receipt in Inbox/Spam.

Any pending alerts are also processed when sending is enabled. Do not share the
new `.env` or the `runtime` folder when uploading another copy of the package.
The email link opens localhost on the PC running this demo; it is not a public
website that an authority can open from another computer.

## What transfers, and what stays on the original PC

The ZIP contains source code, the built website, migrations, sample-data generator,
fixtures, tests, all three launchers, the PPT/PDF, screenshots and documentation.
The optional AI interface and unfinished Flutter starter are included as source
and are clearly identified as future work. No trained AI model is claimed.

The original PC's PostGIS records and uploaded files stay there. The new PC gets
fresh synthetic demo records, not a backup of live complaints. The PPT records the
successful Gmail SMTP test on 7 October 2026; that history does not configure Gmail
on a newly extracted copy. The original test reference will not exist in the new
database; create a new report during rehearsal.

SQLite provides the portable complaint workflow and geometry fallback. The
original installation uses PostgreSQL/PostGIS with spatial indexes. To reproduce
that optional deployment, follow `docs/installation.md`; the portable launchers
do not install or manage Docker.

## Troubleshooting

| Message or symptom | Action |
|---|---|
| Python not found / wrong version | Install 64-bit Python 3.12, reopen the terminal and retry. |
| Missing venv on Ubuntu | Install `python3.12-venv`, then retry. |
| Package download fails | Check internet, proxy and certificate settings. Keep TLS verification enabled; rerun after fixing the cause. |
| Port 8080 already in use | Close the existing demo terminal with Ctrl+C, then retry. |
| Login fails | Read this installation's `runtime/DEMO_CREDENTIALS.md`; passwords from the original PC will not work. |
| Email stays pending | Configure Gmail privately, restart, and keep the app and internet running. |
| Gmail rejects login | Generate a new App Password from the exact sender account; an ordinary Gmail password will not work. |
| Missing map tiles | Internet is needed for the basemap. Forms and stored complaint data still work locally. |
| No PowerPoint installed | Open the supplied PDF in a browser or PDF reader. |

For an advanced first setup on another port, pass `--port 8081` to the launcher
and keep using it on later starts. If changing an existing installation's port,
also update `PUBLIC_URL` and `CORS_ORIGINS` in its private `.env`.

The release is verified by extracting it into a separate folder and exercising
the Linux/SQLite demo. Windows and macOS launchers are supplied; native execution
on those operating systems cannot be tested on this Linux machine.
