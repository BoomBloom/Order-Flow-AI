"""Allow ``python -m ofa.cli`` alongside the installed ``ofa`` script."""

from ofa.cli.main import main

raise SystemExit(main())
