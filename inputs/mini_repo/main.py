from service import get_user_tier


def handle_request(user_id: str) -> str:
    return get_user_tier(user_id)


if __name__ == "__main__":
    print(handle_request("new_user_123"))
