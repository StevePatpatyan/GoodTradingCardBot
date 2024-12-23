import sqlite3


class CardNotFoundError(Exception):
    pass


class TotalCardsExceededError(Exception):
    pass


class NotEnoughCashError(Exception):
    pass


class PackNotAvailableError(Exception):
    pass


def add_card(user_id, card_id):
    conn = sqlite3.connect("cards.db")
    cursor = conn.execute(
        "SELECT NextNumber,total FROM CardsGeneral WHERE id = ?", (card_id,)
    )
    rows = cursor.fetchall()
    if len(rows) == 0:
        raise CardNotFoundError
    next_number = rows[0][0]
    total = rows[0][1]
    if total != None and next_number > total:
        raise TotalCardsExceededError
    conn.execute(
        "INSERT INTO Cards VALUES(NULL, ?, ?, ?)",
        (
            card_id,
            next_number,
            user_id,
        ),
    )
    # iterate next card number to be assigned for the specific card
    conn.execute(
        "UPDATE CardsGeneral SET NextNumber = NextNumber + 1 WHERE id = ?",
        (card_id,),
    )
    conn.commit()
    conn.close()
    return


# transfer cash, vouchers, or cards between 2 people


# transfer_type: cash, vouchers, or card (what is being transferred)
# value: For card, value should be in this format: "#{name}~{number} out of total", and cash/vouchers should be same as transfer_type name
# amount: amount being transferred (only relevant for cash and voucher transfer)
def transfer(transfer_type, value, giver_id, recipient_id, amount=0):
    if (
        transfer_type != "cash"
        and transfer_type != "vouchers"
        and transfer_type != "card"
    ):
        raise ValueError("Invalid transfer value type...")

    conn = sqlite3.connect("cards.db")
    if value == "cash" or value == "vouchers":
        conn.execute(
            f"UPDATE Users SET {value} = {value} - {amount} WHERE id = ?", (giver_id,)
        )
        conn.execute(
            f"UPDATE Users SET {value} = {value} + {amount} WHERE id = ?",
            (recipient_id,),
        )
    else:
        name = value.split("~")[0]
        number = int(
            value.split("~")[1].removesuffix(" out of total").removeprefix("#")
        )
        general_id = conn.execute(
            "SELECT id FROM CardsGeneral WHERE name = ?", (name,)
        ).fetchall()[0][0]
        conn.execute(
            f"UPDATE Cards SET owner_id = ? WHERE general_id = ? AND number = ?",
            (
                recipient_id,
                general_id,
                number,
            ),
        )
    conn.commit()
    conn.close()
