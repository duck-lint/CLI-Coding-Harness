import sys


def main(argv: list[str] | None = None) -> int:
  _ = argv
  print(
    "FAIL: package CLI is not implemented yet. Provider payload "
    "rendering/model call is not available. Use compiler scripts directly "
    "for scaffold validation.",
    file=sys.stderr,
  )
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
