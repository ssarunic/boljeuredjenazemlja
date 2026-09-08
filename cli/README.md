# cadastral_cli: command-line tool

The `cadastral` command (also `uz`, with Croatian command names) for looking up
parcels, owners, land registry units, encumbrances, and parcel geometry.

```bash
pip install -e ./api -e ./cli
cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all
```

Documentation, one page per command, in two languages:

- English: [start here](../docs/en/cli/start-here.md), [complete reference](../docs/en/cli/reference.md), [installation](../docs/en/cli/install.md)
- Hrvatski: [vodič za početak](../docs/hr/cli/start-here.md), [sve naredbe](../docs/hr/cli/reference.md)

Runs against the included mock server only; see [docs/legal.md](../docs/legal.md).
