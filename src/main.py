from static_data import main as run_static_data
from dynamic_data import main as run_dynamic_data
from prepare_data import main as run_prepare_data
from analysis import main as run_analysis


def main():
    print("\nStarting parking pipeline...\n")

    # run_static_data()
    # print("\n" + "-" * 50 + "\n")

    run_dynamic_data()
    print("\n" + "-" * 50 + "\n")

    run_prepare_data()
    print("\n" + "-" * 50 + "\n")

    run_analysis()
    print("\nPipeline finished.\n")


if __name__ == "__main__":
    main()