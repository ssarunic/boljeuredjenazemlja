<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../hr/cli/reference.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it and must not be connected to the official Croatian cadastre or land registry. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Complete reference

<!-- BEGIN GENERATED: reference -->
Every command, with a link to its page. The command is what you type; the link is what it is for.

## Look up one parcel

- `cadastral search`: [Check a parcel quickly](commands/search.md). Quick search for parcels with basic information.
- `cadastral get-parcel`: [See everything the cadastre holds about a parcel](commands/get-parcel.md). Get complete parcel information with ownership details.
- `cadastral get-lr-unit`: [Read the land registry unit: owners, parcels, encumbrances](commands/get-lr-unit.md). Get detailed land registry unit information.

## Look up many parcels at once

- `cadastral batch-fetch`: [Look up a list of parcels at once](commands/batch-fetch.md). Fetch information for multiple parcels in batch mode.
- `cadastral batch-lr-unit`: [Read many land registry units at once](commands/batch-lr-unit.md). Fetch information for multiple land registry units in batch mode.

## Find municipalities and offices

- `cadastral search-municipality`: [Find the number of a cadastral municipality](commands/search-municipality.md). Search and filter municipalities.
- `cadastral list-municipalities`: [List the cadastral municipalities of an office](commands/list-municipalities.md). List municipalities with optional filtering.
- `cadastral list-offices`: [List the cadastral offices](commands/list-offices.md). List all cadastral offices in Croatia.

## Boundaries and maps

- `cadastral get-geometry`: [Get the boundary of a parcel for a map](commands/get-geometry.md). Get parcel boundary coordinates for GIS integration.
- `cadastral download-gis`: [Download the boundary data of a whole municipality](commands/download-gis.md). Download complete GIS data for a municipality.

## Check the tool itself

- `cadastral info`: [Check that the tool is set up](commands/info.md). Display system information and cache status.
- `cadastral cache list`: [See which municipalities are stored on your computer](commands/cache-list.md). List cached municipalities.
- `cadastral cache info`: [See how much boundary data is stored](commands/cache-info.md). Show detailed cache information.
- `cadastral cache clear`: [Remove stored boundary data](commands/cache-clear.md). Clear cached GIS data.
<!-- END GENERATED: reference -->

## Other pages

- [Start here](start-here.md): the tutorial.
- [Glossary](glossary.md): the words of the land registry and the cadastre.
- [Errors](errors.md): what the messages mean.
- [Installation](install.md): for the technical colleague who sets the tool up.
