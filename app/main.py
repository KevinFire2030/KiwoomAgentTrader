from app.workflows.intraday_signal_scan import run_intraday_signal_scan


def main() -> None:
    result = run_intraday_signal_scan(symbol="498270", mode="paper")
    print(result.report)


if __name__ == "__main__":
    main()
