def split_account_name(name: str):
    return name.split(':')


def get_last_account_fragment(account_name: str):
    return split_account_name(account_name)[-1]
