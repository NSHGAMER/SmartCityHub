# Simple placeholder for predictive model (e.g., bin fill-time prediction)
def predict_fill_rate(current_fill, avg_daily_increase=5):
    """Predict how many days until full."""
    remaining = 100 - current_fill
    if avg_daily_increase <= 0:
        return "No prediction"
    days = remaining / avg_daily_increase
    return round(days, 1)

if __name__ == "__main__":
    print(predict_fill_rate(70))  # Example: 6.0 days to full
