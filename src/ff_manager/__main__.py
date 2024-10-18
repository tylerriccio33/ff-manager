import inspect

import click

from ff_manager import main
from ff_manager.filter import PackageFilter, ReceiveFilter, SendFilter


@click.group()
def cli():
    pass


@cli.command()
def print_prof_opts():
    SLEEPER_PROF_EX = """
    platform: "sleeper"
    lineup:
    QB: 1
    RB: 2
    WR: 2
    TE: 1
    FLEX: 2
    SUPERFLEX: 1
    id: ...
    year: 2024
    """
    ESPN_PROF_EX = """
    platform: "espn"

    lineup:
    QB: 1
    RB: 2
    WR: 2
    TE: 1
    FLEX: 2

    s2: ...
    swid: ...
    id: ...
    year: 2024
    """
    click.secho(SLEEPER_PROF_EX, fg="green")
    click.secho(ESPN_PROF_EX, fg="green")


@cli.command()
def print_trade_opts():
    filter_classes = [PackageFilter, ReceiveFilter, SendFilter]
    for cls in filter_classes:
        params = list(inspect.signature(cls).parameters)
        cur_doc_lines: list[str] = cls.__doc__.splitlines()
        for param in params:
            if param in ("self", "kwargs", "args"):
                continue
            desc = next(
                (line.strip() for line in cur_doc_lines if param in line),
                "",
            )
            click.secho(f"\n{param!s}: {desc!s}\n", fg="green", nl=False)


@cli.command(help=main.__doc__)
@click.argument("reqs")
@click.argument(
    "profile",
)
@click.option(
    "--outdate_loc",
)
def find_trades(reqs, profile, outdate_loc=None):
    main(reqs, profile, outdate_loc)


if __name__ == "__main__":
    cli()
