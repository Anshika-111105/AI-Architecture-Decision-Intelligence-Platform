import logging
from typing import Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, TimeSeriesSplit

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Anshika-DataSplit] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ADIP_DataSplit")


class ArchitectureDataSplitter:
    """
    Splits unified ADIP datasets into Train, Validation, and Test sets
    using leakage-safe grouping strategies.
    """

    def __init__(self,
                 train_ratio: float = 0.70,
                 val_ratio: float = 0.15,
                 test_ratio: float = 0.15,
                 random_state: int = 42):
        assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Ratios must sum to 1.0"
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_state = random_state

    def group_split_by_architecture(
        self,
        df: pd.DataFrame,
        group_col: str = "architecture_id"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Splits dataset by architecture group ID. All records belonging to
        a given architecture remain strictly in either Train, Val, or Test.
        """
        if group_col not in df.columns:
            raise KeyError(f"Grouping column '{group_col}' missing from DataFrame.")

        # Step 1: Split into Train+Val vs Test
        gss_test = GroupShuffleSplit(
            n_splits=1,
            test_size=self.test_ratio,
            random_state=self.random_state
        )
        train_val_idx, test_idx = next(gss_test.split(df, groups=df[group_col]))

        train_val_df = df.iloc[train_val_idx].copy()
        test_df = df.iloc[test_idx].copy()

        # Step 2: Split Train+Val into Train and Val
        relative_val_size = self.val_ratio / (self.train_ratio + self.val_ratio)
        gss_val = GroupShuffleSplit(
            n_splits=1,
            test_size=relative_val_size,
            random_state=self.random_state
        )
        train_idx, val_idx = next(gss_val.split(train_val_df, groups=train_val_df[group_col]))

        train_df = train_val_df.iloc[train_idx].copy()
        val_df = train_val_df.iloc[val_idx].copy()

        # Sanity check: Ensure disjoint groups
        train_groups = set(train_df[group_col].unique())
        val_groups = set(val_df[group_col].unique())
        test_groups = set(test_df[group_col].unique())

        assert len(train_groups.intersection(val_groups)) == 0, "Leakage: Train and Val share architectures!"
        assert len(train_groups.intersection(test_groups)) == 0, "Leakage: Train and Test share architectures!"
        assert len(val_groups.intersection(test_groups)) == 0, "Leakage: Val and Test share architectures!"

        logger.info(
            f"Group split complete: Train={len(train_df)} ({len(train_groups)} archs), "
            f"Val={len(val_df)} ({len(val_groups)} archs), "
            f"Test={len(test_df)} ({len(test_groups)} archs)."
        )
        return train_df, val_df, test_df


if __name__ == "__main__":
    # Self-test using mock architecture records
    splitter = ArchitectureDataSplitter()
    mock_data = pd.DataFrame({
        "architecture_id": [f"arch_{i % 10}" for i in range(100)],
        "workload_id": [f"wl_{i}" for i in range(100)],
        "p95": np.random.uniform(10, 500, size=100)
    })
    tr, vl, ts = splitter.group_split_by_architecture(mock_data)
    logger.info("Split module verified and operational.")
