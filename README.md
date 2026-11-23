# Tapo Refresher

A Home Assistant custom integration that periodically calls `refresh_session()` on Tapo P100/P110 smart plugs to prevent KLAP session table exhaustion — the root cause of plugs dropping off Home Assistant with error `1003` ("Network is unstable").

> **Note:** `refresh_session()` re-runs the KLAP handshake without cutting power. Whether it reclaims the existing session slot on the plug's MCU is unconfirmed at firmware level. Effectiveness should be validated empirically over 1-2 weeks of scheduled runs.

---

## Requirements

- Home Assistant 2024.1.0 or newer
- [HACS](https://hacs.xyz/) installed
- Tapo P100 or P110 plugs on **static local IPs** (set DHCP reservations in your router)
- Your Tapo cloud account email and password

---

## Installation

1. Open HACS in Home Assistant
2. Click the three dots (top right) → **Custom repositories**
3. Paste your GitHub repo URL and select **Integration** as the category
4. Click **Add**, then find **Tapo Refresher** in the HACS integration list and install it
5. Restart Home Assistant

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **Tapo Refresher**.

The setup walks through four screens:

### 1. Credentials
Enter your Tapo cloud account email and password. These are stored encrypted in Home Assistant's credential store.

### 2. Add Plugs
Enter the local IP address and a friendly name for each plug. After each entry you can add another plug or continue to the next step.

| Field | Example |
|---|---|
| IP address | `192.168.178.40` |
| Friendly name | `Laptop Charger` |

### 3. Schedule
Choose how often the session refresh runs.

| Frequency | Setting | Example |
|---|---|---|
| Every N minutes | `minutes` + interval (min 5) | Every 30 minutes |
| Every N hours | `hours` + interval | Every 6 hours |
| Daily at a fixed time | `daily` + time (HH:MM) | Daily at `03:00` |

### 4. Notifications
Choose how to be notified when a plug fails.

| Field | Notes |
|---|---|
| Notification service | `Telegram` or `Mobile App` |
| Telegram chat ID | Required if Telegram selected |
| Mobile app device name | Must match the device name in HA (e.g. `my_phone`) |
| Notify on success | Toggle — sends a summary message when all plugs succeed |

**Failure message:** `Tapo plug 'Laptop Charger' (192.168.178.40) failed session refresh: <error>`  
**Success summary:** `Tapo maintenance done: 2/2 plugs refreshed successfully`

---

## Editing After Install

Go to **Settings → Devices & Services**, find **Tapo Refresher**, and click **Configure** to:

- Add or remove plugs
- Change the schedule
- Change notification settings

---

## Manual Trigger

You can trigger a session refresh (or reboot) for any plug manually from **Developer Tools → Actions**:

**Action:** `tapo_refresher.clean_cache`

```yaml
ip_address: "192.168.178.40"
action: refresh_session   # or: reboot (causes brief power interruption)
```

---

## Troubleshooting

**Plug shows as Unavailable before the scheduled refresh runs**  
Trigger `tapo_refresher.clean_cache` manually from Developer Tools, or power-cycle the plug physically (unplug for 5 seconds).

**Authentication error in logs**  
Re-open the integration config and verify your Tapo credentials. Ensure your password contains no special characters that could break the local Python parser.

**Notification not received**  
- Telegram: verify the chat ID is correct and the Telegram integration is set up in HA.
- Mobile App: verify the device name matches exactly (check **Settings → Companion App** in the HA mobile app).

---

## Credits

Session management via the [`tapo`](https://github.com/mihai-dinculescu/tapo) Python library by mihai-dinculescu.
