import aiosqlite
from dotenv import load_dotenv
import os

class CardNotFoundError(Exception):
    pass


class TotalCardsExceededError(Exception):
    pass


class NotEnoughCashError(Exception):
    pass


class PackNotAvailableError(Exception):
    pass


class AlreadyClaimedError(Exception):
    pass


# handle_connection: whether or not to open, commit, and close the db within the function
# conn: the aiosqlite connection to the database (not needed if handle_connection is set to True)
async def add_card(user_id, card_id, handle_connection=True, conn=None):
    if handle_connection:
        conn = await aiosqlite.connect("cards.db")
    cursor = await conn.execute(
        "SELECT NextNumber,total FROM CardsGeneral WHERE id = ?", (card_id,)
    )
    rows = await cursor.fetchall()
    if len(rows) == 0:
        raise CardNotFoundError
    next_number = rows[0][0]
    total = rows[0][1]
    if total != None and next_number > total:
        raise TotalCardsExceededError
    await conn.execute(
        "INSERT INTO Cards VALUES(NULL, ?, ?, ?, 1)",
        (
            card_id,
            next_number,
            user_id,
        ),
    )
    # iterate next card number to be assigned for the specific card
    await conn.execute(
        "UPDATE CardsGeneral SET NextNumber = NextNumber + 1 WHERE id = ?",
        (card_id,),
    )
    if handle_connection:
        await conn.commit()
        await conn.close()
    return


# transfer cash, vouchers, or cards between 2 people


# transfer_type: cash, vouchers, or card (what is being transferred)
# name/number: card name/ card number out of total (CARD TYPE ONLY)
# amount: amount being transferred (only relevant for cash and voucher transfer)
async def transfer(transfer_type, giver_id, recipient_id, name=None, number=None, amount=0):
    if (
        transfer_type != "cash"
        and transfer_type != "vouchers"
        and transfer_type != "card"
    ):
        raise ValueError("Invalid transfer value type...")

    conn = await aiosqlite.connect("cards.db")
    if transfer_type == "cash" or transfer_type == "vouchers":
        await conn.execute(
            f"UPDATE Users SET {transfer_type} = {transfer_type} - {amount} WHERE id = ?",
            (giver_id,),
        )
        await conn.execute(
            f"UPDATE Users SET {transfer_type} = {transfer_type} + {amount} WHERE id = ?",
            (recipient_id,),
        )
    else:
        cursor = await conn.execute(
            "SELECT id FROM CardsGeneral WHERE name = ?", (name,)
        )
        general_id = await cursor.fetchall()
        general_id = general_id[0][0]
        await conn.execute(
            f"UPDATE Cards SET owner_id = ? WHERE general_id = ? AND number = ?",
            (
                recipient_id,
                general_id,
                number,
            ),
        )
    await conn.commit()
    await conn.close()

# total must be either integer value or NULL
async def make_cards(names: list[str], totals: list):
    conn = await aiosqlite.connect("cards.db")

    for i in range(len(names)):
        await conn.execute(f"INSERT INTO CardsGeneral (image, name, total) VALUES (?, ?, ?)", (f"Images/{names[i]}.png", names[i], totals[i] if totals[i] == None else int(totals[i],)))
    
    await conn.commit()
    await conn.close()

# check if user has shiny charm
async def has_shiny_charm(user_id: int):
    load_dotenv(override=True)
    shiny_charm_id = os.getenv("SHINY_CHARM_ID")
    conn = await aiosqlite.connect("cards.db")
    cursor = await conn.execute("SELECT id from Cards WHERE general_id = ? AND owner_id = ?", (shiny_charm_id,user_id,))
    rows = await cursor.fetchall()

    await conn.close()
    return len(rows) > 0
