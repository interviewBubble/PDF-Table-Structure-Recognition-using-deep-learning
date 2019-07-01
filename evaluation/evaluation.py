import os
import sys
import pandas as pd 
from pprint import pprint
import csv
import numpy as np
import tabula
from tqdm import tqdm 
import re
import math
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

def calc_bleu(df_pred, df_gt):
    # Flatten DF on row level
    np_pred_row = np.array([df_pred.columns.values.tolist()] + df_pred.values.tolist())
    np_gt_row = np.array([df_gt.columns.values.tolist()] + df_gt.values.tolist())

    # Flatten DF on column level
    np_pred_col = " ".join(np.transpose(np_pred_row).flatten())
    np_gt_col = " ".join(np.transpose(np_gt_row).flatten())
    np_pred_row = " ".join(np_pred_row.flatten())
    np_gt_row = " ".join(np_gt_row.flatten())
    
    # Calculate the bleu score for row and column arrays
    return [path, sentence_bleu([np_gt_col], np_pred_col, smoothing_function=cc.method6), sentence_bleu([np_gt_row], np_pred_row, smoothing_function=cc.method6)]

def normalize_text(text):
    text = "".join(text.split())
    return re.sub('[^a-zA-Z0-9 \n\.]', '_', text).upper()
    
def get_adjacency_relations(matrix):
    adjacency_relations = []
    for row_idx, row in enumerate(matrix[:-1]):
        for col_idx, col in enumerate(row[:-1]):  
            cell = str(col)
            # Blank cells should not be considered
            if cell == '' or cell == 'nan' or "Unnamed:" in cell:
                continue

            cell = normalize_text(col)         
            next_cell_h, next_cell_v = get_next_cells(matrix, row_idx, col_idx)

            if not next_cell_h == None:
                adjacency_relations.append(('h', cell, next_cell_h))
            if not next_cell_v == None:
                adjacency_relations.append(('v', cell, next_cell_v))
    return adjacency_relations

def get_next_cells(matrix, row_idx, col_idx):
    # Iterate over row, starting from col_idx, until non-empty cell is found
    h = None
    for cell in matrix[row_idx][col_idx+1:]:
        cell = str(cell)
        if not (cell == "" or cell == "nan" or "Unnamed:" in cell):
            h = normalize_text(cell)
            break
    v = None
    for row in matrix[row_idx+1:]:
        cell = str(row[col_idx])
        if not (cell == "" or cell == "nan" or "Unnamed:" in cell):
            v = normalize_text(cell)
            break
    return h, v

def calc_adjacency(df_pred, df_gt):
    pred_matrix = [df_pred.columns.tolist()] + df_pred.values.tolist()
    gt_matrix = [df_gt.columns.tolist()] + df_gt.values.tolist()

    gt_adjacency_relations = get_adjacency_relations(gt_matrix)
    pred_adjacency_relations = get_adjacency_relations(pred_matrix)

    intersection = set(gt_adjacency_relations).intersection(pred_adjacency_relations)
    correct_adj_rel = len(intersection)
    total_adj_rel = len(gt_adjacency_relations)
    detected_adj_rel = len(pred_adjacency_relations)

    if detected_adj_rel == 0:
        if correct_adj_rel == 0:
            precision = 1
        else:
            precision = 0
    else:
        precision = correct_adj_rel / detected_adj_rel

    if total_adj_rel == 0:
        if correct_adj_rel == 0:
            recall = 1
        else:
            recall = 0
    else:
        recall = correct_adj_rel / total_adj_rel

    return precision, recall

if __name__ == '__main__':
    if(len(sys.argv) < 4):
        print("Missing argument. Usage: <pred location> <ground truth location> <type>")
        exit(-1)

    pred_path = sys.argv[1]
    gt_path = sys.argv[2]
    mode = sys.argv[3]
    scores_path = os.path.join(pred_path, 'scores.csv')

    # function used for BLEU score
    cc = SmoothingFunction()

    result_list = []
    for path in tqdm(os.listdir(pred_path)):
        try:
            df_pred = pd.read_csv(os.path.join(pred_path, os.path.splitext(path)[0]+'.csv'), dtype=str)
            df_gt = pd.read_csv(os.path.join(gt_path, os.path.splitext(path)[0]+'.csv'), dtype=str)
            print(df_pred)
            print(df_gt)
            exit()
            # drop completely empty rows and columns
            df_pred = df_pred.dropna(how='all', axis=0)
            df_pred = df_pred.dropna(how='all', axis=1)

            if mode == 'bleu':
                result_list.append(calc_bleu(df_pred, df_gt))
            else:
                precision, recall = calc_adjacency(df_pred, df_gt)
                result_list.append([path, precision, recall])
        except Exception as e:
            result_list.append([path, 0, 0])
            continue

    if mode == 'bleu':
        result_df = pd.DataFrame(result_list, columns=['file', 'bleu_col7', 'bleu_row7'])
    else:
        result_df = pd.DataFrame(result_list, columns=['file', 'precision', 'recall'])

    grouped = result_df.copy()
    grouped['category'] = grouped['file'].apply(lambda x: x.split("-")[0])
    grouped['file'] = grouped['file'].apply(lambda x: x.split("-")[1])
    
    result_df.to_csv(scores_path)
    grouped.groupby('category').mean().to_csv(os.path.splitext(scores_path)[0] + '-grouped' + '.csv')        
