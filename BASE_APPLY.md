# Clipcart Base Patch

Apply this patch from the Clipcart repository root. Replace files at the same paths, and add new files.

The patch intentionally does not include `node_modules/`, `.env` files, Python caches, or generated invoice files. Keep your local secrets outside version control.

The following old admin starter assets were removed from the rebuilt base and may be deleted locally if they are still present:

- `admin-frontend/src/assets/hero.png`
- `admin-frontend/src/assets/react.svg`
- `admin-frontend/src/assets/vite.svg`

Do not replace a working local `.env` with the example; copy `.env.example` only when creating a new environment.

Base validation performed here: Python sources compile successfully. Full frontend/backend runtime builds were not executed in this environment because the uploaded archive's dependency folders were intentionally excluded from the rebuilt baseline.