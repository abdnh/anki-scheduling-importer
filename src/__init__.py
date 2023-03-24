from __future__ import annotations

import functools
import time
import zipfile

from anki.cards import Card, CardId
from anki.collection import Collection, OpChangesWithCount
from anki.consts import CardQueue, CardType
from anki.utils import tmpfile
from aqt import mw
from aqt.operations import CollectionOp
from aqt.qt import *
from aqt.utils import getFile, tooltip


def on_import_scheduling() -> None:
    file = getFile(
        mw, title="Choose file to import scheduling info from", cb=None, filter="*.apkg"
    )
    if not file:
        return

    def import_op(col: Collection) -> OpChangesWithCount:
        assert isinstance(file, str)
        zip = zipfile.ZipFile(file)
        col_bytes = zip.read(f"collection.anki21")
        colpath = tmpfile(suffix=".anki21")
        with open(colpath, "wb") as f:
            f.write(col_bytes)
        src = Collection(colpath)
        dst = col
        total_cards = src.db.scalar("select count() from cards")
        dst_cards: dict[tuple[str, int], CardId] = {}
        for guid, ord, cid in dst.db.execute(
            "select f.guid, c.ord, c.id from cards c, notes f where c.nid = f.id"
        ):
            dst_cards[(guid, ord)] = cid
        guids = set(dst.db.list("select guid from notes"))
        cards: list[Card] = []
        revlog = []
        last_progress = 0.0
        want_cancel = False

        def update_progress(label: str, value: int, max: int) -> None:
            nonlocal want_cancel
            want_cancel = mw.progress.want_cancel()
            mw.progress.update(label, value=value, max=max)

        for row in src.db.execute(
            "select n.guid, c.ord, c.type, c.queue, c.due, c.ivl, c.factor, c.reps, c.lapses, c.left, c.odue, c.odid, c.flags from cards c, notes n where c.nid = n.id"
        ):
            if time.time() - last_progress >= 0.1:
                last_progress = time.time()
                mw.taskman.run_on_main(
                    functools.partial(
                        update_progress,
                        f"Processed {len(cards)} cards out of {total_cards}",
                        len(cards),
                        total_cards,
                    )
                )
            if want_cancel:
                break
            guid = row[0]
            ord = row[1]
            if guid not in guids or (guid, ord) not in dst_cards:
                continue
            cid = dst_cards[(guid, ord)]
            type = CardType(row[2])
            queue = CardQueue(row[3])
            due = row[4]
            ivl = row[5]
            factor = row[6]
            reps = row[7]
            lapses = row[8]
            left = row[9]
            odue = row[10]
            odid = row[11]
            flags = row[12]
            card = dst.get_card(cid)
            card.type = type
            card.queue = queue
            card.due = due
            card.ivl = ivl
            card.factor = factor
            card.reps = reps
            card.lapses = lapses
            card.left = left
            card.odue = odue
            card.odid = odid
            card.flags = flags
            cards.append(card)
            for rev in src.db.execute("select * from revlog where cid = ?", cid):
                rev = list(rev)
                rev[2] = dst.usn()
                revlog.append(rev)

        dst.db.executemany(
            """insert or ignore into revlog values (?,?,?,?,?,?,?,?,?)""", revlog
        )
        src.close()
        os.remove(colpath)
        undo_entry = dst.add_custom_undo_entry("Import scheduling info")
        dst.update_cards(cards)
        changes = dst.merge_undo_entries(undo_entry)
        return OpChangesWithCount(count=len(cards), changes=changes)

    def on_success(changes: OpChangesWithCount) -> None:
        tooltip(f"Updated {changes.count} cards")

    CollectionOp(mw, op=import_op).success(success=on_success).run_in_background()


action = QAction("Import scheduling info from deck package", mw)
qconnect(action.triggered, on_import_scheduling)
mw.form.menuTools.addAction(action)
