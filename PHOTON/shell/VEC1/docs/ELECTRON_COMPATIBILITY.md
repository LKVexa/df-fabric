# Electron Compatibility Surface

| Electron concept | VEC1 v0.2.0 equivalent | Status |
|---|---|---|
| main process | Python VEC control plane | reference implemented |
| renderer process | system Edge/Chrome app-mode window | reference implemented |
| `ipcMain` / `ipcRenderer.invoke` | loopback JSON RPC (`/api/...`) | reference implemented |
| preload bridge | `ui/app.js` API calls | reference implemented |
| BrowserWindow | one system-browser app window | partial |
| app lifecycle | start/stop shell, `POST /api/shutdown`, enforced ACTIVE/SUSPENDED/RETIRED electron lifecycle | partial |
| Node integration | deliberately absent | not implemented |
| context isolation | browser origin + CSP + no Node API + isolated browser profile + Host/Origin/token-guarded IPC | implemented for reference shell |
| native modules | future Host-Call/Plugin Gate | blocked/not implemented |
| filesystem APIs | VEC runtime state sandbox only | partial |
| network APIs | VEC outbound network denied/not implemented | partial |
| menus/dialogs/tray | none | not implemented |
| DevTools | browser engine DevTools, plus VEC inspector dashboard | partial |
| updater/signing | VM package mechanisms only; shell updater absent | not implemented |

This package is therefore an **Electron substitute architecture/reference shell**, not an API-compatible clone.
