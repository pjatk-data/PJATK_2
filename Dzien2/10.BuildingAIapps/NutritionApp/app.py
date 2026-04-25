import os
from typing import List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

st.set_page_config(
    page_title="Creative Nutrition Planner", page_icon="🥗", layout="wide"
)

st.title("🥗 Creative Nutrition Planner")
st.write(
    "Select ingredients, track the calories, and let AI craft a delicious recipe using your choices."
)

INGREDIENTS = [
    {
        "Ingredient": "Grilled Chicken Breast",
        "Serving": "100 g",
        "Calories": 165,
        "Protein (g)": 31,
        "Carbs (g)": 0,
        "Fat (g)": 3.6,
    },
    {
        "Ingredient": "Quinoa",
        "Serving": "1/2 cup cooked",
        "Calories": 111,
        "Protein (g)": 4.1,
        "Carbs (g)": 19.7,
        "Fat (g)": 1.8,
    },
    {
        "Ingredient": "Baby Spinach",
        "Serving": "1 cup",
        "Calories": 7,
        "Protein (g)": 0.9,
        "Carbs (g)": 1.1,
        "Fat (g)": 0.1,
    },
    {
        "Ingredient": "Cherry Tomatoes",
        "Serving": "1 cup",
        "Calories": 27,
        "Protein (g)": 1.3,
        "Carbs (g)": 5.8,
        "Fat (g)": 0.3,
    },
    {
        "Ingredient": "Avocado",
        "Serving": "1/2 medium",
        "Calories": 117,
        "Protein (g)": 1.5,
        "Carbs (g)": 6,
        "Fat (g)": 10.5,
    },
    {
        "Ingredient": "Roasted Sweet Potato",
        "Serving": "1/2 cup",
        "Calories": 90,
        "Protein (g)": 2,
        "Carbs (g)": 21,
        "Fat (g)": 0.1,
    },
    {
        "Ingredient": "Black Beans",
        "Serving": "1/2 cup",
        "Calories": 114,
        "Protein (g)": 7.6,
        "Carbs (g)": 20.4,
        "Fat (g)": 0.5,
    },
    {
        "Ingredient": "Feta Cheese",
        "Serving": "28 g",
        "Calories": 75,
        "Protein (g)": 4,
        "Carbs (g)": 1.1,
        "Fat (g)": 6,
    },
    {
        "Ingredient": "Toasted Almonds",
        "Serving": "2 tbsp",
        "Calories": 66,
        "Protein (g)": 2.5,
        "Carbs (g)": 2.3,
        "Fat (g)": 5.8,
    },
    {
        "Ingredient": "Fresh Basil",
        "Serving": "1/4 cup",
        "Calories": 5,
        "Protein (g)": 0.6,
        "Carbs (g)": 1,
        "Fat (g)": 0.1,
    },
]

df = pd.DataFrame(INGREDIENTS)

st.subheader("Ingredient Reference Table")
st.dataframe(df, width="stretch", hide_index=True)

st.sidebar.header("Build Your Meal")
available_ingredients = [row["Ingredient"] for row in INGREDIENTS]
selected_ingredients = st.sidebar.multiselect(
    "Select ingredients",
    available_ingredients,
    help="Pick items to add them to your meal.",
)

selected_rows = df[df["Ingredient"].isin(selected_ingredients)]
total_calories = int(selected_rows["Calories"].sum()) if not selected_rows.empty else 0

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Your Meal Basket")
    if selected_rows.empty:
        st.info("Start by selecting ingredients from the sidebar.")
    else:
        st.table(
            selected_rows.set_index("Ingredient")[
                ["Serving", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
            ]
        )

with col2:
    st.subheader("Quick Stats")
    st.metric(label="Total Calories", value=f"{total_calories} kcal")

# Ensure recipe output is retained across reruns.
if "recipe" not in st.session_state:
    st.session_state.recipe = ""

st.markdown("---")
st.subheader("Generate a Creative Recipe")
st.write(
    "Click the button below to ask the AI for an inspiring recipe based on your chosen ingredients."
)


def create_client() -> OpenAI | None:
    """Return an OpenAI client when an API key is available."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
    base_url = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not api_key or not base_url:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)


def generate_recipe(ingredients: List[str], total_kcal: int) -> str:
    """Generate a recipe using the selected ingredients via the OpenAI Responses API."""
    client = create_client()
    if not client:
        return "⚠️ No OpenAI API key detected. Set OPENAI_API_KEY or AZURE_OPENAI_API_KEY to enable recipe generation."

    prompt = (
        "You are an imaginative chef. Compose a mouth-watering recipe using only the provided ingredients. "
        "Return the response as rich text with bullet points for steps. Include a short story-like introduction, "
        "detailed cooking steps, and serving suggestions. Avoid inventing extra ingredients."
    )
    user_input = (
        "Ingredients: "
        + ", ".join(ingredients)
        + f". Total calorie target: approximately {total_kcal} kcal."
    )

    try:
        response = client.responses.create(
            model=os.getenv("AZURE_OPENAI_COMPLETION_MODEL")
            or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ],
        )
    except OpenAIError as exc:
        return f"❌ The AI request failed: {exc}"

    try:
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text
        return response.output[0].content[0].text
    except (AttributeError, IndexError, KeyError):
        return "❌ Received an unexpected response format from the AI service."


if st.button("Generate Recipe", disabled=not selected_ingredients):
    if not selected_ingredients:
        st.warning("Please select at least one ingredient before generating a recipe.")
    else:
        with st.spinner("Cooking up something delicious..."):
            st.session_state.recipe = generate_recipe(
                selected_ingredients, total_calories
            )

if st.session_state.recipe:
    st.markdown("### AI-Crafted Recipe")
    st.write(st.session_state.recipe)
