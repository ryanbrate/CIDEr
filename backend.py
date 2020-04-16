#!/usr/bin/env python
# coding: utf-8

# In[13]:

import json

import numpy as np
import pandas as pd

decimals = 2
threshold = 0


def backend(
    file, row_indices, column_indices, time_column=None, start_time=None, end_time=None
):

    # Read the excel file

    df = pd.read_excel(file, header=row_indices, index_col=column_indices)
    df = df.reset_index()

    if row_indices[-1] > 0:
        df.columns = [" ".join(col) for col in df.columns]

    # account for time_column entry

    time_column = df.columns[time_column - 1]
    if start_time and end_time:
        df = df[(df[time_column] >= start_time) & (df[time_column] <= end_time)]
        print(
            "The function is calling the right thing!",
            start_time,
            end_time,
            df[time_column],
        )
    else:
        pass

    # Level 0

    level_0 = {}
    corr_matrix = df.corr("spearman")
    corr_matrix = corr_matrix.where(np.triu(np.ones(corr_matrix.shape)).astype(np.bool))
    result = round(
        corr_matrix[(corr_matrix < 1) & (abs(corr_matrix) > threshold)]
        .unstack()
        .sort_values(ascending=False)
        .dropna(),
        decimals,
    )
    first = [i[0] for i in result.keys()]
    second = [i[1] for i in result.keys()]
    corr = list(result.values)
    corr_abs = list(abs(result.values))
    level_0["corr"] = list(zip(first, second, corr, corr_abs))

    # Level 1

    if column_indices[-1] > 0:
        level_1 = {}
        for sub in df[df.columns[0]].unique():
            dictionary = {}
            sub_column = df.columns[0]
            mask = df[df[sub_column] == sub]
            mask_categories = mask[mask.columns[1]].unique()
            corr_matrix = mask.corr("spearman")
            corr_matrix = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape)).astype(np.bool)
            )
            result = round(
                corr_matrix[(corr_matrix < 1) & (abs(corr_matrix) > threshold)]
                .unstack()
                .sort_values(ascending=False)
                .dropna(),
                decimals,
            )
            first = [i[0] for i in result.keys()]
            second = [i[1] for i in result.keys()]
            corr = list(result.values)
            corr_abs = list(abs(result.values))
            dictionary["corr"] = list(zip(first, second, corr, corr_abs))

            # Level 2

            if column_indices[-1] > 1:
                level_2 = {}
                for sub2 in mask_categories:
                    dictionary2 = {}
                    sub_column = df.columns[1]
                    mask = df[df[sub_column] == sub2]
                    corr_matrix = mask.corr("spearman")
                    corr_matrix = corr_matrix.where(
                        np.triu(np.ones(corr_matrix.shape)).astype(np.bool)
                    )
                    result = round(
                        corr_matrix[(corr_matrix < 1) & (abs(corr_matrix) > threshold)]
                        .unstack()
                        .sort_values(ascending=False)
                        .dropna(),
                        decimals,
                    )
                    first = [i[0] for i in result.keys()]
                    second = [i[1] for i in result.keys()]
                    corr = list(result.values)
                    corr_abs = list(abs(result.values))
                    dictionary2["corr"] = list(zip(first, second, corr, corr_abs))
                    level_2[sub2] = dictionary2
                dictionary["subs"] = level_2

            level_1[sub] = dictionary

        level_0["subs"] = level_1

    return level_0
