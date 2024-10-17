from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
@app.route("/home")
def domovska_stranka():
    return render_template("index.html")

@app.route("/profil")
def dejv_kralos():
    return render_template("profil.html")

@app.route("/mapik")
def mapik():
    return render_template("mapik.html")

@app.route("/chabri")
def chabri():
    return render_template("chabri.html")

@app.route("/nastaveni")
def nastaveni():
    return render_template("nastaveni.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0",  port=4000, debug=True)
