# 🎴 Trading Card Discord Bot

This is my **Trading Card Discord Bot**, a customizable system where users can collect, trade, and earn virtual cards.  
You can use this as a base for your own project — the structure is flexible, and you can easily modify it to match your own schema or theme.

My implementation uses **family and personal photos** as the card images, but you can substitute these with any images of your choice.

---

## 🗃️ Database Overview

The bot uses a few main tables to manage data:

- **CardsGeneral** — stores metadata for each card type  
- **Cards** — stores specific instances of cards owned by users  
- **Users** — stores user balances and data  
- **Packs** — defines packs that can be opened  
- **VoucherRewards**, **Questions**, **SetRewards**, and **Codes** — additional systems for special rewards and bonuses  

> 💡 The current version assumes the user interacting with the bot is already registered in the database.

---

## 📚 General Schema

### **CardsGeneral**
| Field | Description |
|-------|--------------|
| `id` | General card ID (or cash/voucher ID) |
| `image` | Image path of the card |
| `name` | Card name |
| `total` | Total number of cards available (∞ if `NULL`) |
| `NextNumber` | Next number for new cards (e.g., if there are 4 of a card, NextNumber = 5) |

---

### **Cards**
| Field | Description |
|-------|--------------|
| `id` | Specific card ID |
| `general_id` | Foreign key → `CardsGeneral.id` |
| `number` | Card’s number within its type |
| `owner_id` | Discord ID of the card owner (`Users.id`) |
| `tradable` | Whether the card can be traded (`0` = No, `1` = Yes) |

---

### **Users**
| Field | Description |
|-------|--------------|
| `id` | Discord user ID |
| `username` | Discord username |
| `cash` | User’s current cash |
| `vouchers` | Number of vouchers owned |
| `LastLogin` | Timestamp of last login (for login bonuses) |
| `SetsClaimed` | IDs of claimed set rewards (comma-separated) |
| `CodesClaimed` | IDs of claimed codes (comma-separated) |

---

### **Packs**
| Field | Description |
|-------|--------------|
| `name` | Pack name |
| `cost` | Cash cost of the pack |
| `CommonDrop` | ID of common drop |
| `UncommonDrop` | ID of uncommon drop |
| `RareDrop` | ID of rare drop |
| `EpicDrop` | ID of epic drop |
| `LegendaryDrop` | ID of legendary drop |
| `MythicalDrop` | ID of mythical drop |
| `available` | Whether the pack is available (`0` = No, `1` = Yes) |
| `CashBase` | Base cash reward if drop rewards cash |
| `VoucherBase` | Base voucher reward if drop rewards vouchers |
| `description` | Description of the pack |

---

### **VoucherRewards**
| Field | Description |
|-------|--------------|
| `cost` | Cost of reward in vouchers |
| `reward_id` | General reward ID (`CardsGeneral.id`) |
| `available` | Availability (`0` = No, `1` = Yes) |
| `name` | Name of the event (used in `useVouchers` command) |
| `CashRewarded` | Cash amount if reward is cash |
| `description` | Description of the voucher reward |

---

### **Questions**
*(Used for login bonuses)*

| Field | Description |
|-------|--------------|
| `question` | Question text |
| `answer1`–`answer4` | Multiple-choice answers |
| `correct` | The correct answer |

---

### **SetRewards**
| Field | Description |
|-------|--------------|
| `id` | Unique set reward ID |
| `name` | Name of the set reward |
| `reward_id` | ID of the reward (`-1` / `-2` for cash/vouchers) |
| `CardsRequired` | Comma-separated IDs of required cards |
| `description` | Description of the set reward |
| `quantity` | Amount of cash/vouchers given if applicable |

---

### **Codes**
| Field | Description |
|-------|--------------|
| `id` | Unique code ID |
| `name` | Display name of the reward |
| `reward_id` | ID of reward (`-1` / `-2` for cash/vouchers) |
| `quantity` | Amount of cash/vouchers if applicable |
| `available` | Availability (`0` = No, `1` = Yes) |
| `code` | The code string users enter to claim reward |

---

## 🎲 Odds and Customization

> ⚠️ **Note:** Odds and drop rates may change between commits.  
You can tweak your own odds by modifying:
- The `rolls` variable in the code
- The end condition of the iteration or `while` loop

This allows full control over pack rarity balance and reward distribution.

---

## 🧩 How to Customize

- Replace images in `CardsGeneral` with your own collection  
- Modify schemas for your preferred structure  
- Adjust drop rates, rewards, and login bonuses to match your gameplay style  

---

**Happy Collecting! 🎉**
