This is my trading card discord bot. The following code should be good to use for anyone. I have the trading cards as images of family including myself.

The database schema I use for cards involves the general card info table as well as the table of specific cards tied to an owner and number out of the total of that particular card type. One can modify the code for themselves to fit a different schema!

There is also a Users table which stores cash and voucher balance of a user as well as Packs table which stores info about packs that users can open.

For now, the code assumes the person interacting with the bot is registered in the database,

General Schema:

CardsGeneral:

- id - general card id (or cash/voucher id)
- image - image path of card
- name - card name
- total - total number of cards available (infinite if NULL)
  NextNumber - next number of the card if a new one is generated (EX: If there are 4 of a card, NextNumber is 5)

Cards:

- id: specific card id
- general_id: general card id (foreign key of id in CardsGeneral)
- number: number of the card compared to all of the cards of its type
- owner_id: discord id of the owner of the card (foreign key of id in Users)
- tradable: whether or not the card can be traded (0 for no, 1 for yes)

Users:

- id: discord user id
- username: discord username
- cash: cash amount of user
- vouchers: number of vouchers user has
- LastLogin: last time user has logged in (stored to check if user has already claimed login bonus)
- SetsClaimed: set rewards that user claimed (as they cannot claim them again). Format is set ids separated by commas
- CodesClaimed: codes that user claimed (as they cannot claim them again). Format is code ids separated by commas

  Packs:

- name: pack name
- cost: cash cost of pack
- CommonDrop: id of common drop
- UncommonDrop: id of uncommon drop
- RareDrop: id of rare drop
- EpicDrop: id of epic drop
- LegendaryDrop: id of legendary drop
- MythicalDrop: id of mythical drop
- available: whether or not pack is available (0 if unavailable or 1 if available)
- CashBase: base value of cash rewarded if drop rewards cash (see openPack command)
- VoucherBase: base value of vouvhers rewarded if drop rewards vouchers
- description - description of pack

VoucherRewards:

- cost: cost of reward in vouchers
- reward_id: general id of reward (CardsGeneral id)
- available: availability of reward (0 if unavailable, 1 if available)
- name: name of event that user will type as parameter of useVouchers command
- CashRewarded: amount of cash voucher gives if reward is cash
- description: description of reward

Questions (used for login bonus for now):

- question: the question in question
- answer1: one answer choice
- answer2: another answer choice
- answer3: another answer choice
- answer4: another answer choice
- correct: the actual correct answer to the question

SetRewards:

- id: unique id of the set reward
- name: name of the set reward displayed
- reward_id: id of the card given (or -1/-2 if cash/vouchers)
- CardsRequired: card_ids of cards required to claim set reward separated by commas
- description: description of set reward
- quantity: amount of cash/vouchers given if that is the reward

Codes:

- id: unique id of code
- name: name of the reward displayed
- reward_id: id of the card given (or -1/-2 for cash/vouchers)
- quantity: amount of cash/vouchers given if that is a reward
- available: 0 if code is not available and 1 if it is
- code: the code to claim the reward

**NOTE: I may change how odds work between commits. Modify rolls variable in the code and at end of iteration or the while loop condition to make your own odds**
