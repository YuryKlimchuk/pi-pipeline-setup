# PoC примитивов установщика (Track B)

> **Синтетические fixtures.** Все provider/ID, содержимое и пути — вымышленные;
> секретов и реальных производственных настроек нет. Это **provisional**-прототип
> для проверки примитивов D3, а **не** финальный контракт D3/P6a и не production-установщик.

## Объём (утверждён Gate A: задачи 0.2, 3.1–3.10)

- `poc_installer.py` — provisional-примитивы: manifest, `plan` (без записи), `apply`
  (staging/backup/journal/state), `recover`, детект symlink/hardlink и drift.
- `test_poc_installer.py` — офлайн-тесты (`unittest`, только stdlib; пишет только в
  одноразовый temp-каталог).
- `installer/install-manifest.json` — пример provisional-manifest с четырьмя типами
  владения и хешами управляемых частей.

## Manifest (provisional)

```json
{
  "schemaVersion": 1,
  "provisional": true,
  "entries": [
    {"path": "…", "ownership": "whole-file | json-keys | marked-block | frontmatter-fields",
     "desired": "…", "sha256": "…"}
  ]
}
```

- `whole-file` — файл управляется целиком.
- `json-keys` — управляются только перечисленные ключи JSON (остальные сохраняются).
- `marked-block` — управляется блок между `<!-- BEGIN <blockId> -->` / `<!-- END <blockId> -->`.
- `frontmatter-fields` — управляются только перечисленные скалярные поля YAML-frontmatter
  (PoC-упрощение: только `key: value`-скаляры; формальная обработка — P4/P6a).

`sha256` — хеш канонической формы управляемой части (информативен; установщик
пересчитывает и сверяет по канонической форме).

## Согласование (D3-примитивы)

`plan()`: `create` (отсутствует) / `noop` (current == desired) / `update`
(current == last-applied) / `conflict` (drift — пользователь изменил управляемую часть).
`apply()`: staging → backup → write-ahead journal → запись → фиксация `state.json`
последней. `recover()`: откат незавершённой транзакции по journal+backup.

## Запуск

```bash
cd tests/fixtures/installer-agent-role-poc
python3 test_poc_installer.py
```

Ожидание: все тесты зелёные. Ничего вне одноразового temp-каталога не пишется.
