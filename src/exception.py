class NoValuesError(Exception):
    def __init__(self, obj_name: str):
        super().__init__(f"There must be values passed to {obj_name}.")


class CorrespondError(Exception):
    def __init__(self, x: str, y: str):
        msg = f"Values of {x} and {y} must logically correspond."
        super().__init__(msg)

class AssetNameError(Exception):
    def __init__(self, asset_name, valid_assets: list):
        super().__init__(f"`{asset_name}` is not a valid asset. \
            Choose from -> {valid_assets}")
