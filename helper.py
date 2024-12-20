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
    if next_number > total:
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
