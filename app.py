from pathlib import Path

import plotly.express as px
import plotly.graph_objs as go
import streamlit as st
import pandas as pd

TARGET_DIR='data'
TARGET_CSV='data.csv'

BASE_DIR=Path(__file__).resolve().parent
DATA_PATH=BASE_DIR / TARGET_DIR / TARGET_CSV