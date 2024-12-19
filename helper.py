import sqlite3


def addCard(user_id, card_id):
    conn = sqlite3.connect("cards.db")
    cursor = conn.execute(
        "SELECT NextNumber FROM CardsGeneral WHERE id = ?", (card_id,)
    )
    rows = cursor.fetchall()
    if len(rows) == 0:
        print("No such card...")
        conn.close()
        return
    next_number = rows[0][0]
    cursor = conn.execute(
        "INSERT INTO Cards VALUES(NULL, ?, ?, ?)",
        (
            card_id,
            next_number,
            user_id,
        ),
    )
    conn.commit()
    # iterate next card number to be assigned for the specific card
    cursor = conn.execute(
        "UPDATE CardsGeneral SET NextNumber = NextNumber + 1 WHERE id = ?",
        (card_id,),
    )
    conn.commit()
    conn.close()
    return
