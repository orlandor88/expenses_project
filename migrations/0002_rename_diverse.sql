-- Migration: rename category DIverse -> Diverse
BEGIN TRANSACTION;
UPDATE categorii SET categorie = 'Diverse' WHERE categorie = 'DIverse';
COMMIT;
