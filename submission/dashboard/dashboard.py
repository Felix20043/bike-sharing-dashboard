import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set Page Config
st.set_page_config(
    page_title="Bike Sharing Dashboard",
    page_icon="🚲",
    layout="wide"
)

sns.set_theme(style='whitegrid')

# ==============================================================================
# 1. DEFINISI FUNGSI PEMROSESAN DATA
# ==============================================================================

def create_daily_orders_df(df):
    """Menyiapkan DataFrame ringkasan harian"""
    # Mengelompokkan berdasarkan tanggal dteday
    daily_orders_df = df.groupby('dteday').agg({
        'cnt': 'sum',
        'registered': 'sum',
        'casual': 'sum'
    }).reset_index()
    return daily_orders_df

def create_season_weather_df(df):
    """Menyiapkan DataFrame untuk Analisis Pengaruh Cuaca dan Musim"""
    p1_df = df.pivot_table(index='season', columns='weathersit', values='cnt', aggfunc='mean')
    p1_df['Drop_Percent'] = ((p1_df['Clear/Partly Cloudy'] - p1_df['Light Snow/Rain']) / p1_df['Clear/Partly Cloudy']) * 100
    return p1_df

def create_hourly_peak_df(df_hour):
    """Menyiapkan DataFrame untuk Analisis Jam Sibuk Pengguna"""
    reg_work = df_hour[df_hour['workingday'] == 1].groupby('hr')['registered'].mean().reset_index()
    cas_holiday = df_hour[df_hour['workingday'] == 0].groupby('hr')['casual'].mean().reset_index()
    
    offpeak_reg_mean = reg_work[~reg_work['hr'].isin([8, 17, 18])]['registered'].mean()
    offpeak_cas_mean = cas_holiday[~cas_holiday['hr'].isin(list(range(11, 18)))]['casual'].mean()
    
    return reg_work, cas_holiday, offpeak_reg_mean, offpeak_cas_mean

def create_eda_monthly_df(df):
    """Agregasi tren bulanan per tahun"""
    return df.groupby(['yr', 'mnth'])['cnt'].mean().reset_index()

def create_eda_user_ratio_df(df):
    """Proporsi Total Penyewaan Berdasarkan Tipe Pengguna"""
    total_casual = df['casual'].sum()
    total_registered = df['registered'].sum()
    return pd.DataFrame({
        'User Type': ['Casual', 'Registered'],
        'Total': [total_casual, total_registered]
    })

def create_eda_corr_matrix(df):
    """Matriks korelasi parameter numerik lingkungan"""
    numeric_cols = ['temp', 'atemp', 'hum', 'windspeed', 'cnt']
    valid_cols = [c for c in numeric_cols if c in df.columns]
    return df[valid_cols].corr()

# ==============================================================================
# 2. LOAD DATASET
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

day_df = pd.read_csv(os.path.join(BASE_DIR, "main_data.csv"))
hour_df = pd.read_csv(os.path.join(BASE_DIR, "hour_cleaned.csv"))

day_df['dteday'] = pd.to_datetime(day_df['dteday'])
hour_df['dteday'] = pd.to_datetime(hour_df['dteday'])

min_date = day_df['dteday'].dt.date.min()
max_date = day_df['dteday'].dt.date.max()

# ==============================================================================
# 3. SIDEBAR (FILTER RENTANG WAKTU)
# ==============================================================================

with st.sidebar:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.image("https://cdn-icons-png.flaticon.com/512/2972/2972185.png", width=150)
    
    st.markdown("<h3 style='text-align: center;'>Bike Sharing App</h3>", unsafe_allow_html=True)
    st.write("")

    date_range = st.date_input(
        label='Rentang Waktu',
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date],
        key="main_date_filter"
    )

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = min_date
    end_date = max_date

# Filter main_day_df
main_day_df = day_df[
    (day_df['dteday'] >= pd.to_datetime(start_date)) & 
    (day_df['dteday'] <= pd.to_datetime(end_date))
]

# Filter main_hour_df
main_hour_df = hour_df[
    (hour_df['dteday'] >= pd.to_datetime(start_date)) & 
    (hour_df['dteday'] <= pd.to_datetime(end_date))
]

# ==============================================================================
# 4. MEMANGGIL FUNGSI (DATA SUDAH TERSEDIA)
# ==============================================================================

daily_orders_df = create_daily_orders_df(main_day_df)
p1_df = create_season_weather_df(main_day_df)
reg_work, cas_holiday, offpeak_reg_mean, offpeak_cas_mean = create_hourly_peak_df(main_hour_df)

# ==============================================================================
# 5. DASHBOARD UI (HEADER & METRIK SUMMARY)
# ==============================================================================

st.header("🚲 Bike Sharing Performance Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    total_orders = daily_orders_df['cnt'].sum()
    st.metric("Total Penyewaan", value=f"{total_orders:,}")

with col2:
    total_registered = daily_orders_df['registered'].sum()
    st.metric("Pengguna Registered", value=f"{total_registered:,}")

with col3:
    total_casual = daily_orders_df['casual'].sum()
    st.metric("Pengguna Casual", value=f"{total_casual:,}")

st.markdown("---")

# ==============================================================================
# 6. VISUALISASI DATA (2 PERTANYAAN SMART)
# ==============================================================================

# ------------------------------------------------------------------------------
# GRAFIK 1: PENGARUH CUACA BURUK (SMART 1)
# ------------------------------------------------------------------------------
st.subheader("1. Pengaruh Cuaca Buruk Terhadap Penurunan Penyewaan Harian")

fig1, ax1 = plt.subplots(figsize=(10, 5))
sns.barplot(
    data=main_day_df,
    x='season',
    y='cnt',
    hue='weathersit',
    estimator='mean',
    errorbar=None,
    palette='Set2',
    ax=ax1
)

ax1.set_title('Penurunan Penyewaan Harian Saat Cuaca Buruk (>50% Drop)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Musim (Season)', fontsize=10)
ax1.set_ylabel('Rata-rata Penyewaan Harian (cnt)', fontsize=10)
ax1.legend(title='Kondisi Cuaca', loc='upper left')

# Menambahkan anotasi persentase penurunan pada grafik
seasons = main_day_df['season'].unique()
for i, season in enumerate(['Spring', 'Summer', 'Fall', 'Winter']):
    if season in p1_df.index and 'Light Snow/Rain' in p1_df.columns:
        drop_val = p1_df.loc[season, 'Drop_Percent']
        blue_bar_height = p1_df.loc[season, 'Light Snow/Rain']
        
        ax1.text(
            i + 0.27, blue_bar_height + 250, f'Drop: {drop_val:.1f}%', 
            ha='center', va='bottom', fontsize=8, fontweight='bold', 
            color='red', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='red')
        )

st.pyplot(fig1)

# ------------------------------------------------------------------------------
# GRAFIK 2: LONJAKAN JAM SIBUK (SMART 2)
# ------------------------------------------------------------------------------
st.subheader("2. Perbandingan Jam Sibuk Pengguna Registered vs Casual")

fig2, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 5))

# Plot 1: Registered (Hari Kerja)
sns.lineplot(data=reg_work, x='hr', y='registered', marker='o', color='#2ecc71', linewidth=2, ax=ax_left)
ax_left.axhline(offpeak_reg_mean * 3.5, color='red', linestyle='--', label=f'Threshold 3.5x ({offpeak_reg_mean*3.5:.1f})')
ax_left.set_title('Pengguna Registered pada Hari Kerja (Lonjakan > 3.5x)', fontsize=11, fontweight='bold')
ax_left.set_xlabel('Jam (00:00 - 23:00)', fontsize=9)
ax_left.set_ylabel('Rata-rata Penyewaan / Jam', fontsize=9)
ax_left.set_xticks(range(0, 24))
ax_left.grid(True, linestyle='--', alpha=0.5)
ax_left.legend()

for hr in [8, 17, 18]:
    if hr in reg_work['hr'].values:
        val = reg_work[reg_work['hr'] == hr]['registered'].values[0]
        ratio = val / offpeak_reg_mean
        ax_left.text(hr, val + 15, f'{ratio:.1f}x', ha='center', fontsize=8, fontweight='bold', color='darkgreen')

# Plot 2: Casual (Hari Libur)
sns.lineplot(data=cas_holiday, x='hr', y='casual', marker='o', color='#e74c3c', linewidth=2, ax=ax_right)
ax_right.axhline(offpeak_cas_mean * 3.5, color='red', linestyle='--', label=f'Threshold 3.5x ({offpeak_cas_mean*3.5:.1f})')
ax_right.set_title('Pengguna Casual pada Hari Libur (Lonjakan > 3.5x)', fontsize=11, fontweight='bold')
ax_right.set_xlabel('Jam (00:00 - 23:00)', fontsize=9)
ax_right.set_ylabel('Rata-rata Penyewaan / Jam', fontsize=9)
ax_right.set_xticks(range(0, 24))
ax_right.grid(True, linestyle='--', alpha=0.5)
ax_right.legend()

for hr in range(11, 18):
    if hr in cas_holiday['hr'].values:
        val = cas_holiday[cas_holiday['hr'] == hr]['casual'].values[0]
        ratio = val / offpeak_cas_mean
        ax_right.text(hr, val + 5, f'{ratio:.1f}x', ha='center', fontsize=8, fontweight='bold', color='darkred')

st.pyplot(fig2)

eda_monthly_df = create_eda_monthly_df(main_day_df)
eda_user_ratio_df = create_eda_user_ratio_df(main_day_df)
eda_corr_df = create_eda_corr_matrix(main_day_df)

col_eda1, col_eda2 = st.columns(2)

# Subplot 1: Tren Bulanan per Tahun
with col_eda1:
    st.markdown("**Tren Rata-rata Penyewaan Bulanan**")
    fig_eda1, ax_eda1 = plt.subplots(figsize=(8, 5))
    sns.lineplot(data=eda_monthly_df, x='mnth', y='cnt', hue='yr', marker='o', ax=ax_eda1, palette='tab10')
    ax_eda1.set_xlabel('Bulan', fontsize=9)
    ax_eda1.set_ylabel('Rata-rata Penyewaan', fontsize=9)
    ax_eda1.set_xticks(range(1, 13))
    ax_eda1.legend(title='Tahun')
    st.pyplot(fig_eda1)

# Subplot 2: Proporsi Tipe Pengguna
with col_eda2:
    st.markdown("**Proporsi Total Pengguna (Casual vs Registered)**")
    fig_eda2, ax_eda2 = plt.subplots(figsize=(8, 5))
    ax_eda2.pie(
        eda_user_ratio_df['Total'], 
        labels=eda_user_ratio_df['User Type'], 
        autopct='%1.1f%%', 
        startangle=90, 
        colors=['#ff9999', '#66b3ff']
    )
    ax_eda2.axis('equal')
    st.pyplot(fig_eda2)

# Subplot 3: Heatmap Korelasi Parameter Lingkungan
st.markdown("**Matriks Korelasi Variabel Lingkungan & Jumlah Penyewaan**")
fig_eda3, ax_eda3 = plt.subplots(figsize=(8, 4))
sns.heatmap(eda_corr_df, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5, ax=ax_eda3)
st.pyplot(fig_eda3)

st.caption("Copyright © 2026 - Bike Sharing Analysis")
