<?php
declare(strict_types=1);
/* PHP 8.2 PDO does not track a transaction opened with raw BEGIN SQL. Use
 * PDO's transaction API and acquire SQLite's write reservation immediately,
 * before any SELECT snapshot. The zero-row UPDATE changes no outbox data. */
function st_transaction_begin(PDO $db): void {
    $db->beginTransaction();
    try{$db->exec('UPDATE outbox SET id=id WHERE 0');}
    catch(Throwable $error){if($db->inTransaction())$db->rollBack();throw $error;}
}
