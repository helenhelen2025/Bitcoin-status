import streamlit as st
import pyupbit
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np

# 한글 폰트 설정
import platform
import matplotlib.font_manager as fm

def set_korean_font():
    """운영체제별 한글 폰트 설정"""
    system = platform.system()
    
    if system == 'Windows':
        # Windows
        font_name = 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        font_name = 'AppleGothic'
    else:  # Linux (Streamlit Cloud 환경)
        font_name = 'NanumGothic' # Streamlit Cloud는 Nanum 폰트가 설치되어 있을 가능성이 높음
    
    try:
        plt.rcParams['font.family'] = font_name
    except:
        # 폰트가 없을 경우 대체 폰트 사용
        plt.rcParams['font.family'] = 'DejaVu Sans'
    
    plt.rcParams['axes.unicode_minus'] = False

# 한글 폰트 적용
set_korean_font()

st.title("📈 Upbit 비트코인 현황 대시보드")

# 사이드바 설정
st.sidebar.header("설정")
chart_period = st.sidebar.selectbox(
    "차트 기간 선택",
    ["1일", "3일", "7일", "30일"],
    index=2
)

# 기간별 설정
period_map = {
    "1일": ("day", 1),
    "3일": ("day", 3), 
    "7일": ("day", 7),
    "30일": ("day", 30)
}

unit, count = period_map[chart_period]

# 현재가 정보
st.header("💰 현재가 정보")
col1, col2 = st.columns(2)

try:
    # 현재가 조회
    btc_price = pyupbit.get_current_price("KRW-BTC")
    
    if btc_price is not None:
        with col1:
            st.metric(
                label="비트코인 현재가 (KRW)", 
                value=f"{btc_price:,} 원"
            )
        
        # 24시간 전 가격과 비교
        yesterday_price = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=2)
        if yesterday_price is not None and len(yesterday_price) >= 2:
            prev_price = yesterday_price.iloc[-2]['close']
            change = btc_price - prev_price
            change_percent = (change / prev_price) * 100
            
            with col2:
                st.metric(
                    label="24시간 변동",
                    value=f"{change:+,.0f} 원",
                    delta=f"{change_percent:+.2f}%"
                )
    else:
        st.warning("⚠️ 비트코인 현재 가격을 가져올 수 없습니다. API 요청 제한 또는 네트워크 문제를 확인하세요.")
    
    # 차트 데이터 조회
    st.header("📊 차트 분석")
    
    # OHLCV 데이터 조회
    df = pyupbit.get_ohlcv("KRW-BTC", interval=unit, count=count)
    
    if df is not None and not df.empty:
        # 인덱스를 datetime으로 변환
        df.index = pd.to_datetime(df.index)
        
        # 이동평균 계산
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=min(20, len(df))).mean()
        
        # 차트 생성
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Bitcoin {chart_period} Chart Analysis', fontsize=16, fontweight='bold')
        
        # 1. 가격 차트 (선 그래프)
        ax1.plot(df.index, df['close'], label='Close Price', color='#FF6B35', linewidth=2)
        ax1.plot(df.index, df['MA5'], label='MA5', color='blue', alpha=0.7)
        if len(df) >= 20:
            ax1.plot(df.index, df['MA20'], label='MA20', color='red', alpha=0.7)
        ax1.set_title('Price Trend', fontweight='bold')
        ax1.set_ylabel('Price (KRW)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 2. 캔들스틱 차트 (간단한 바 차트로 구현)
        colors = ['red' if close >= open_price else 'blue' 
                          for close, open_price in zip(df['close'], df['open'])]
        ax2.bar(range(len(df)), df['high'] - df['low'], 
                        bottom=df['low'], color=colors, alpha=0.6, width=0.8)
        ax2.set_title('Candlestick Chart', fontweight='bold')
        ax2.set_ylabel('Price (KRW)')
        ax2.set_xticks(range(0, len(df), max(1, len(df)//5)))
        ax2.set_xticklabels([df.index[i].strftime('%m-%d') 
                                 for i in range(0, len(df), max(1, len(df)//5))])
        
        # 3. 거래량 차트
        ax3.bar(df.index, df['volume'], color='skyblue', alpha=0.7)
        ax3.set_title('Volume', fontweight='bold')
        ax3.set_ylabel('Volume')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 4. 변동성 차트 (일일 변동폭)
        daily_change = ((df['high'] - df['low']) / df['close'] * 100)
        ax4.plot(df.index, daily_change, color='purple', marker='o', markersize=3)
        ax4.axhline(y=daily_change.mean(), color='red', linestyle='--', 
                            label=f'Average: {daily_change.mean():.2f}%')
        ax4.set_title('Daily Volatility (%)', fontweight='bold')
        ax4.set_ylabel('Volatility (%)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # 통계 정보
        st.header("📈 통계 정보")
        col1, col2, col3, col4 = st.columns(4)
        
        # 숫자 포맷팅 함수
        def format_number(num):
            if num >= 100000000:  # 1억 이상
                return f"{num/100000000:.1f}억"
            elif num >= 10000:  # 1만 이상
                return f"{num/10000:.1f}만"
            else:
                return f"{num:,.0f}"
        
        with col1:
            st.metric("High Price", f"{format_number(df['high'].max())} KRW")
        with col2:
            st.metric("Low Price", f"{format_number(df['low'].min())} KRW")
        with col3:
            st.metric("Avg Volume", f"{format_number(df['volume'].mean())}")
        with col4:
            st.metric("Avg Volatility", f"{daily_change.mean():.2f}%")
        
        # 투자매력도 지수 계산
        st.header("💎 투자매력도 지수")
        
        def calculate_investment_score(df, current_price):
            """투자매력도 지수 계산 (0-100점)"""
            scores = {}
            
            # 1. 추세 점수 (30점) - MA5 > MA20이면 상승추세
            if len(df) >= 20 and df['MA5'].iloc[-1] > df['MA20'].iloc[-1]:
                trend_score = 30
                trend_status = "상승 추세 🟢"
            elif len(df) >= 5 and df['close'].iloc[-1] > df['MA5'].iloc[-1]:
                trend_score = 20
                trend_status = "단기 상승 🟡"
            else:
                trend_score = 10
                trend_status = "하락/보합 🔴"
            scores['trend'] = (trend_score, trend_status)
            
            # 2. 변동성 점수 (25점) - 적절한 변동성이 좋음
            volatility = daily_change.mean()
            if 2 <= volatility <= 5:  # 적절한 변동성
                vol_score = 25
                vol_status = "적정 변동성 🟢"
            elif 1 <= volatility < 2 or 5 < volatility <= 8:
                vol_score = 18
                vol_status = "보통 변동성 🟡"
            else:
                vol_score = 10
                vol_status = "높은 변동성 🔴"
            scores['volatility'] = (vol_score, vol_status)
            
            # 3. 거래량 점수 (20점) - 최근 거래량이 평균보다 높으면 좋음
            recent_volume = df['volume'].tail(3).mean()
            avg_volume = df['volume'].mean()
            volume_ratio = recent_volume / avg_volume
            
            if volume_ratio > 1.5:
                volume_score = 20
                volume_status = "높은 거래량 🟢"
            elif volume_ratio > 1.0:
                volume_score = 15
                volume_status = "보통 거래량 🟡"
            else:
                volume_score = 8
                volume_status = "낮은 거래량 🔴"
            scores['volume'] = (volume_score, volume_status)
            
            # 4. 가격 위치 점수 (15점) - 최근 가격이 중간~상단에 있으면 좋음
            price_range = df['high'].max() - df['low'].min()
            current_position = (current_price - df['low'].min()) / price_range
            
            if 0.6 <= current_position <= 0.8:
                position_score = 15
                position_status = "좋은 가격대 🟢"
            elif 0.4 <= current_position < 0.6 or 0.8 < current_position <= 0.9:
                position_score = 10
                position_status = "보통 가격대 🟡"
            else:
                position_score = 5
                position_status = "극단 가격대 🔴"
            scores['position'] = (position_score, position_status)
            
            # 5. 수익률 점수 (10점) - 최근 수익률
            if len(df) >= 7:
                week_return = (current_price - df['close'].iloc[-7]) / df['close'].iloc[-7] * 100
                if week_return > 5:
                    return_score = 10
                    return_status = "높은 수익률 🟢"
                elif week_return > 0:
                    return_score = 7
                    return_status = "양수 수익률 🟡"
                else:
                    return_score = 3
                    return_status = "음수 수익률 🔴"
            else:
                return_score = 5
                return_status = "데이터 부족 ⚪"
            scores['return'] = (return_score, return_status)
            
            total_score = sum([score[0] for score in scores.values()])
            return total_score, scores
        
        # 투자매력도 계산
        investment_score, score_details = calculate_investment_score(df, btc_price)
        
        # 투자매력도 표시
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # 점수에 따른 색상 및 등급 결정
            if investment_score >= 80:
                grade = "A+"
                color = "#00C851"  # 녹색
                recommendation = "강력 매수 추천"
            elif investment_score >= 70:
                grade = "A"
                color = "#2E7D32"
                recommendation = "매수 추천"
            elif investment_score >= 60:
                grade = "B+"
                color = "#FFC107"  # 노란색
                recommendation = "신중한 매수"
            elif investment_score >= 50:
                grade = "B"
                color = "#FF8F00"
                recommendation = "관망"
            elif investment_score >= 40:
                grade = "C"
                color = "#FF5722"  # 주황색
                recommendation = "신중한 관망"
            else:
                grade = "D"
                color = "#F44336"  # 빨간색
                recommendation = "매수 비추천"
            
            # 큰 점수 표시
            st.markdown(f"""
            <div style="text-align: center; background-color: {color}20; padding: 20px; border-radius: 10px; border: 2px solid {color};">
                <h1 style="color: {color}; margin: 0;">{investment_score}점</h1>
                <h3 style="color: {color}; margin: 0;">{grade} 등급</h3>
                <p style="color: {color}; margin: 0; font-size: 16px;"><strong>{recommendation}</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        # 세부 점수 표시
        st.subheader("📊 세부 평가 항목")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            trend_score, trend_status = score_details['trend']
            st.metric("추세 분석", f"{trend_score}/30", help=trend_status)
        
        with col2:
            vol_score, vol_status = score_details['volatility']
            st.metric("변동성", f"{vol_score}/25", help=vol_status)
        
        with col3:
            volume_score, volume_status = score_details['volume']
            st.metric("거래량", f"{volume_score}/20", help=volume_status)
        
        with col4:
            position_score, position_status = score_details['position']
            st.metric("가격대", f"{position_score}/15", help=position_status)
        
        with col5:
            return_score, return_status = score_details['return']
            st.metric("수익률", f"{return_score}/10", help=return_status)
        
        # 평가 기준 설명
        with st.expander("💡 투자매력도 평가 기준"):
            st.markdown("""
            **평가 항목별 배점:**
            - **추세 분석 (30점)**: 이동평균선 기반 상승/하락 추세 판단
            - **변동성 (25점)**: 적절한 변동성(2-5%) 여부 평가
            - **거래량 (20점)**: 최근 거래량이 평균 대비 활발한지 평가
            - **가격대 (15점)**: 현재 가격이 최근 범위 내 적절한 위치인지 평가
            - **수익률 (10점)**: 최근 1주일간 수익률 평가
            
            **등급 기준:**
            - A+ (80점 이상): 강력 매수 추천
            - A (70-79점): 매수 추천  
            - B+ (60-69점): 신중한 매수
            - B (50-59점): 관망
            - C (40-49점): 신중한 관망
            - D (40점 미만): 매수 비추천
            
            ⚠️ **주의**: 이는 참고용 지표이며, 실제 투자 결정은 신중히 하시기 바랍니다.
            """)
        
        # 최근 데이터 테이블
        st.header("📋 최근 데이터")
        recent_data = df.tail(10).copy()
        recent_data.index = recent_data.index.strftime('%Y-%m-%d %H:%M')
        recent_data = recent_data.round(0)
        st.dataframe(
            recent_data[['open', 'high', 'low', 'close', 'volume']],
            use_container_width=True
        )
        
    else:
        st.error("❌ 차트 데이터를 가져올 수 없습니다. Upbit API에 문제가 있거나, 선택된 기간에 데이터가 없을 수 있습니다.")
        
except ModuleNotFoundError:
    st.error("❌ 'pyupbit' 모듈을 찾을 수 없습니다. Streamlit Cloud에 앱을 배포하는 경우 `requirements.txt` 파일에 `pyupbit`를 추가했는지 확인해주세요.")
    st.info("로컬에서 실행하는 경우, 터미널에서 `pip install pyupbit`를 실행하여 설치해주세요.")
except Exception as e:
    st.error(f"❌ 오류 발생: {str(e)}")
    st.info("네트워크 연결 상태와 라이브러리 설치를 확인해주세요.")

# 자동 새로고침 (선택적)
if st.sidebar.checkbox("자동 새로고침 (30초)"):
    import time
    time.sleep(30)
    st.rerun()

# 푸터
st.markdown("---")
st.markdown("**📊 데이터 제공:** Upbit API | **⏰ 업데이트:** 실시간")
st.markdown("**💡 팁:** 사이드바에서 차트 기간을 변경할 수 있습니다.")