<<<<<<< HEAD
# WhatsApp Bulk Sender Web UI

Aa project local computer par browser ma web UI open kari WhatsApp Desktop thi bulk message + image send karva mate che.

Important: Aa app WhatsApp Desktop ne keyboard/mouse automation thi chalave che. Etle aa app tamara Windows PC par run karvi jaruri che. Normal live Linux server/VPS par aa direct kaam nahi kare, karan ke tya WhatsApp Desktop GUI hotu nathi.

## Features

- Browser ma web UI
- Excel upload
- Image upload
- Common message textbox
- Start / Stop button
- Live log
- Sent / inactive / failed count
- Single tick / double tick aave tya sudhi next number par nahi jay
- WhatsApp par active na hoy eva numbers ni alag Excel report

## Requirements

- Windows PC
- Python 3.10 ke latest
- WhatsApp Desktop installed ane login thayelu
- Internet connection
- Excel file jema `phone` naam ni column hoy

## Setup

Project folder open karo:

```powershell
cd "C:\Users\dhruv\Downloads\Whatsapp message send\Whatsapp message send"
```

Python libraries install karo:

```powershell
py -m pip install -r requirements.txt
```

Jo `py` command na chale to:

```powershell
python -m pip install -r requirements.txt
```

## Run

App start karo:

```powershell
py namechange.py
```

Browser automatic open thase. Jo automatic open na thay to aa URL open karo:

```text
http://127.0.0.1:8000/
```

Jo port 8000 busy hoy to app next free port par start thase. Terminal ma URL check kari levo.

## Excel Format

Excel file ma `phone` column compulsory che.

Example:

| phone |
| --- |
| 9876543210 |
| 919876543210 |
| 09876543210 |

Script number clean kari ne Indian 10 digit format ma convert karse.

## Web UI Use

1. Message box ma tamaro message paste karo.
2. Excel file select karo.
3. Image file select karo.
4. `Max messages` set karo.
5. `Tick timeout seconds` set karo.
   - `0` rakho to script single/double tick confirm thay tya sudhi wait karse.
   - Example `120` rakho to 120 seconds pachi tick confirm na thay to stop karse.
6. `Start` button press karo.
7. WhatsApp Desktop automation chalse. Mouse/keyboard touch na karvu.
8. End ma report links web UI ma visible thase.

## Reports

Run complete thay pachi reports download links web UI ma male:

- `whatsapp_inactive_numbers.xlsx`
  - invalid numbers
  - WhatsApp par active na hoy / chat open na thay eva numbers

- `whatsapp_failed_report.xlsx`
  - failed numbers
  - inactive numbers
  - tick confirm na thay eva cases
  - error reason

Reports project na `media/reports/` folder ma save thay che.

## Stop Process

`Stop` button press karsho to current WhatsApp step complete/close thaya pachi script stop thase. Direct window close karva karta Stop button use karvo.

## Notes

- WhatsApp Desktop already login hovu joiye.
- Automation chalta time mouse/keyboard disturb na karvu.
- Pehla 1-2 test numbers thi test karvu.
- WhatsApp bulk sending par restriction muki shake che, etle small batches ma send karvu.
- Live server par production system joiye to WhatsApp Business Cloud API use karvi pade. Aa desktop automation local PC mate che.

## Common Problems

### Excel must contain phone column

Excel ma column name exactly `phone` hovu joiye.

### WhatsApp open thatu nathi

WhatsApp Desktop install/login che ke nahi check karo.

### UI check dependency missing

Dependencies install karo:

```powershell
py -m pip install -r requirements.txt
```

### Port already in use

`py namechange.py` auto next port choose karse. Terminal ma printed URL open karo.
=======
# whatsapp_message_sender_automation
>>>>>>> a588bbe136979146399b8b1e61a0ff8ddba26ddd
