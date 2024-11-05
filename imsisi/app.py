from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/recommendation')
def recommendation():
    return render_template('recommendation.html')

@app.route('/parking')
def parking():
    return render_template('parking.html')

@app.route('/map')
def map_view():
    return render_template('map.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

if __name__ == '__main__':
    app.run(debug=True)
