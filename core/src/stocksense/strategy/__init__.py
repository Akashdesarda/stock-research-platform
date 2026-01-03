import polars as pl

from .analysis import TechnicalAnalysis


def register_ta():
    """
    Explicitly registers the 'ta' namespace with Polars.
    Call this once at the start of your application or script.
    """
    # Importing the analysis module triggers the @pl.api.register_dataframe_namespace decorator
    from . import analysis

    # This block helps the IDE (Pylance/MyPy) understand that pl.DataFrame has a 'ta' property.
    # Note: This is a type hint patch and does not affect runtime behavior.

    # We use a dummy property to tell the type checker that 'ta' returns a TechnicalAnalysis instance.
    # This works because Pylance merges this declaration with the library stub.

    # Patching the type hint for the imported polars module
    pl.DataFrame.ta: TechnicalAnalysis
    pl.LazyFrame.ta: TechnicalAnalysis
