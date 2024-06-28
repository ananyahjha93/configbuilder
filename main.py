import sys

from configs.config import ConfigClassC, clean_opt, CliError


def main(cfg: ConfigClassC):
    print(cfg)


if __name__ == "__main__":
    try:
        yaml_path, args_list = sys.argv[1], sys.argv[2:]
    except IndexError:
        raise CliError(f"Usage: {sys.argv[0]} [CONFIG_PATH] [OPTIONS]")

    cfg = ConfigClassC.load(yaml_path, [clean_opt(s) for s in args_list])
    main(cfg)
