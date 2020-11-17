from flask import Flask, request, redirect, render_template, flash, session, g, abort, url_for, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Recipe, UserRecipe
from forms import RegisterForm, LoginForm, UserEditForm
from werkzeug.exceptions import Unauthorized
from sqlalchemy.exc import IntegrityError
import os, requests
from helper import search_recipes, get_recipe, add_recipe_db, valid_cuisines,valid_diets, get_visual_ingredients
from secrets import API_Key

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL','postgresql:///recipes')
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','izURL73j^nu24Bp')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///recipes'
app.config['SECRET_KEY'] = 'SECRET'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

app.config['DEBUG_TB_INTERCEPT_REDIRECTS']= False
 
debug = DebugToolbarExtension(app)
 
connect_db(app)

##############################################################################
# User signup/login/logout
    
@app.before_request
def add_user_to_g():
    """Register a user: produce form and handle form submission"""
    
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

def do_login(user):
    session[CURR_USER_KEY] = user.username

def do_logout(user):
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/register',methods=['GET','POST'])
def register():
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = RegisterForm()

    if form.validate_on_submit():
        try:
            user = User.register(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username already taken", 'danger')
            return render_template('users/register.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/register.html', form=form)
   
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate():
        user = User.authenticate(
            form.username.data,
            form.password.data)

        if user: 
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect('/')
        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html',form=form)

@app.route('/logout')
def logout():
    """Handle logout of user."""
    user = g.user
    do_logout(user)

    flash("You have successfully logged out.", 'success')
    return redirect("/login")

##############################################################################
# General user routes:

@app.route('/')
def home_page():
    """show landing page for register or sign in"""
    
    return render_template('index.html')

@app.route("/users/<username>")
def show_user(username):
    """show profile of an user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get(username)

    return render_template("users/detail.html", user=user)

@app.route("/users/<username>/edit", methods=["GET", "POST"])
def edit_user(username):
    """Show update user form and process it."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    user = g.user

    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user.password = form.password.data
        user.email = form.email.data
        user.img_url = form.img_url.data
        db.session.commit()

        return redirect(f"/users/{username}")
        
        # flash("Wrong password, please try again.", 'danger')

    return render_template("users/edit.html", form=form, user=user)

@app.route("/users/<username>/delete", methods=["POST"])
def remove_user(username):
    """Remove user and redirect to login."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout(username)

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/register")

##############################################################################
# Routes:

@app.route("/")
def show_homepage():
    """show the homepage with the search form"""
    if not g.user:
        flash("Please login to view.", "warning")
        return redirect('/login')
    print("XXXXX")
    data = search_recipes(request)
    print("???????")
    recipes = data['results']
    print(recipes)

    return render_template("index.html", recipes=recipes)

# Recipe routes:
@app.route("/recipes/<int:id>")
def show_recipe_details(id):
    """show the recipe details"""
    if not g.user:
        flash("Please login to view.","warning")
        return redirect('/login')

    recipe = Recipe.query.filter_by(id=id).first()
    data = get_recipe(id).json()
    recipe = add_recipe_db(data)
    
    return render_template("recipes/detail.html", recipe=recipe)

# favorite routes:
@app.route("/favorites")
def show_fav_recipes():
    """show saved favorite recipes"""
    if not g.user:
        flash("Please login to view.","warning")
        return redirect('/login')
    recipe_list = [recipe.id for recipe in g.user.recipes]

    return render_template("favs/show.html", recipe_list=recipe_list)


@app.route("/favorites/<int:id>", methods=['POST'])
def add_favorites():
    """add favorite recipes"""
    if not g.user:
        flash("Please login to view.","warning")
        return redirect('/login')
    
    recipe = Recipe.query.filter_by(id=id).first()
    if not recipe:
        data = get_recipe(id)
        recipe = add_recipe_db(data)
        g.user.recipes.append(recipe)
        db.session.commit()
    else:
        g.user.recipes.append(recipe)
        db.session.commit()
    
    response_json = jsonify(recipe = recipe.serialize(),message="Recipe added!")
    return (response_json,200)
        
@app.route('/favorites/<int:id>', methods=['DELETE'])
def remove_favorites():
    """unfavorite a recipe"""
    if not g.user:
        return abort(401)
    
    recipe = Recipe.query.filter_by(id=id).first()
    UserRecipe.query.filter(UserRecipe.username == g.user.username, UserRecipe.recipe_id == recipe.id).delete()
    
    db.session.commit()
    response_json = jsonify(recipe=recipe.serialize(),message="Recipe removed!")

    return (response_json,200)

    


        


    
















##############################################################################
# Homepage and error pages



# @app.errorhandler(404)
# def page_not_found(e):
#     """404 NOT FOUND page."""

#     return render_template('404.html'), 404


##############################################################################
# Turn off all caching in Flask

# @app.after_request
# def add_header(req):
#     """Add non-caching headers on every request."""

#     req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     req.headers["Pragma"] = "no-cache"
#     req.headers["Expires"] = "0"
#     req.headers['Cache-Control'] = 'public, max-age=0'
#     return req