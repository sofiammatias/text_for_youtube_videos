import streamlit as st
from translate import Translator
import re
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title='YouTube Videos Description Builder', layout="wide", page_icon='🎦')

# Initializing some constants

path_ings_links = r'ings_links.csv'
path_equip_links = r'equip_links.csv'
path_affiliates = r'C:\Users\xufia\OneDrive\Documentos\Artesanal - Sabonetes, cremes, oleos, ambientadores\HERBALCOCHETE\_thirstyaffiliates-export-20240526131155-affiliate-links.csv'
path_posts = r'C:\Users\xufia\OneDrive\Documentos\Artesanal - Sabonetes, cremes, oleos, ambientadores\HERBALCOCHETE\Backups\backup-2024\herbalcochete.WordPress.2024-05-26-posts.xml'
path_recipes = r'C:\Users\xufia\OneDrive\Documentos\Artesanal - Sabonetes, cremes, oleos, ambientadores\HERBALCOCHETE\Backups\backup-2024\herbalcochete.WordPress.2024-05-26-recipes.xml'
no_post_str = '-No Post-'
no_recipe_str = '-No Recipe-'
desc_text = '-No Description-'
xml_recipes_file =  open(path_recipes, 'rb')
xml_posts_file =  open(path_posts, 'rb')
affiliates_df = pd.read_csv(path_affiliates)
metric_units = ['g', 'ml']
imperial_units = ['oz', 'fl.oz']
g_to_oz = 0.035274
ml_to_floz = 0.033814

posts_list = [no_post_str]
recipes_list = [no_recipe_str]
list_ingredients = pd.DataFrame([])
list_ingredients_oz = pd.DataFrame([])
list_equipment = pd.DataFrame([])
items_text = ''
if 'item_links' not in st.session_state:
    st.session_state.item_links = items_text
if 'ingredients' not in st.session_state:
    st.session_state.ingredients = list_ingredients
if 'equipment' not in st.session_state:
    st.session_state.equipment = list_equipment




# Some Functions

def convert_value_to_oz (value:int,meas:str):
    """Converts a value from g or ml to oz or fl.oz"""
    meas = meas.strip()
    if meas in metric_units:
        if meas == metric_units[0]: # grams
            new_value = value * g_to_oz
        if meas == metric_units[1]: # mililiters
            new_value = value * ml_to_floz
    else:
        new_value = value
    return new_value

def convert_unit_to_oz (meas:str):
    """Converts a unit to oz or fl.oz"""
    meas = meas.strip()
    if meas.strip() in metric_units:
        if meas == metric_units[0]: # grams
            new_meas = imperial_units[0]
        if meas == metric_units[1]: # mililiters
            new_meas = imperial_units[1]
    else:
        new_meas = meas
    return new_meas


# Read files
# - posts file
if xml_posts_file is not None:
    tree_posts = ET.parse(xml_posts_file)
    for elm in tree_posts.findall(".//item/title"):
        if elm.text[0].isupper():
            posts_list.append(elm.text)
        else:
            continue

# - recipes file
if xml_recipes_file is not None:
    tree_recipes = ET.parse(xml_recipes_file)
    for item_node in tree_recipes.findall('.//item/title'):
        if item_node.text[0].isupper():
            recipes_list.append(item_node.text)

# - affiliate links csv file
if len(affiliates_df) != 0:
    affiliates_df = affiliates_df.iloc[:, : 3]
    affiliates_df.rename(columns = {'Destination URL': 'Url'}, inplace = True)


# Sidebar
with st.sidebar:
    num_char = st.number_input("Insert number of characters for post description:", min_value = 0, max_value = 15000, value=500)

    # Get title and description from chosen post
    post_title = st.selectbox ("Get a post for description:", posts_list) 
    if post_title != no_post_str:
        for item_node in tree_posts.findall('.//item'):
            if item_node.find('title').text == post_title:
                desc_node = item_node.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                if desc_node is not None:
                    desc_text = str(desc_node.text)
                    clean_text = re.sub(r"[\(\<].*?[\>)]", "", desc_text).replace('\n', '')
                    desc_text = clean_text[:num_char]
    
    # Get list of ingredients and equipment from chosen recipe
    recipe_title = st.selectbox ("Get a recipe for list of ingredients + equipment:", recipes_list) 
    if recipe_title != no_recipe_str:
        for item_node in tree_recipes.findall('.//item'):
            if item_node.find('title').text == recipe_title:
                for wprm_node in item_node.findall('{http://wordpress.org/export/1.2/}postmeta'):
                    # Get ingredients
                    if (wprm_node[0].tag == '{http://wordpress.org/export/1.2/}meta_key') and (wprm_node[0].text == 'wprm_ingredients'):
                        text_aux = pd.Series(wprm_node[1].text.split('"'))
                        text = pd.Series([txt for txt in text_aux[2:] if (len(txt) != 0) and (txt[0] != ';') ])
                        ingredients = []
                        for i in range (len(text)):
                            if (text[i] == 'amount'):
                                if (text[i+1] == 'unit'):
                                    dictz = {'amount': 0, 'unit': 'None', 'name': text[i+3] + ' ' + text[i+5]}
                                else:
                                    dictz = {'amount': float(text[i+1].replace(',', '.')), 'unit': text[i+3], 'name': text[i+5]}
                                ingredients.append (dictz)
                        list_ingredients = pd.DataFrame(ingredients)
                        # Change units
                        df = list_ingredients.copy()
                        df['amount'] = list_ingredients.apply(lambda row : convert_value_to_oz(row[0], row[1]), axis=1).round(2)
                        df['unit'] = list_ingredients.apply(lambda row : convert_unit_to_oz(row.unit), axis=1)
                        list_ingredients_oz = df.copy()

                    # Get equipment
                    if (wprm_node[0].tag == '{http://wordpress.org/export/1.2/}meta_key') and (wprm_node[0].text == 'wprm_equipment'):
                        text_aux = pd.Series(wprm_node[1].text.split('"'), name = 'equipments')
                        index = [txt[0].isupper() if len(txt) != 0 else False for txt in text_aux]
                        list_equipment = pd.DataFrame(text_aux[index]).reset_index()
                        list_equipment = list_equipment.drop('index', axis=1)

    option = st.selectbox ("See List:", ('None', 'Ingredients', 'Equipment'))
    if option == 'Ingredients':
        st.dataframe (list_ingredients_oz, use_container_width = True)
    if option == 'Equipment':
        st.dataframe (list_equipment, use_container_width = True)


# Title
st.title("YouTube Video Descriptions W/ Affiliate Links 🎦")

tab1, tab2 = st.tabs(["Descriptions in English", "Descriptions in Portuguese"])

# Main window
# Prepare text description for videos in English
with tab1:

    # Interface to choose links
    st.write ("Choose links:")
    links = st.dataframe(
        affiliates_df[affiliates_df.Zone == 'EN'],
        height = 250,
        column_config={
            "name": st.column_config.TextColumn("name"),
            "url": st.column_config.TextColumn("URL")
        },
        hide_index=True,

        on_select="rerun",
        selection_mode="multi-row",
        )

    col1, col2 = st.columns (2)

    with col1:
        # List of links to add
        st.write ('Edit links table:')
        links_shortlist = st.data_editor(affiliates_df.iloc[links.selection['rows']], num_rows="dynamic", use_container_width=True, key = '11')

        st.write ('Use file for:')
        col11, col12 = st.columns(2)
        with col11:
            check_file_ings = st.checkbox("Ingredients links", key = '1')
        with col12:
            check_file_equip = st.checkbox("Equipment links", key = '2')


    with col2: 
        st.write ('Final links list:')
        st.dataframe(links_shortlist, use_container_width=True)
        st.write ("Add links for:")

        col21, col22, col23 = st.columns(3)

        with col21:
            if st.checkbox ("Ingredients", key = '3'):
                if check_file_ings:
                    list_ingredients_oz = pd.read_csv(path_ings_links)
                else:
                    list_ingredients_oz['url'] = links_shortlist['Url']
                st.session_state.ingredients = list_ingredients_oz

        with col22:
            if st.checkbox("Equipment", key = '4'): 
                if check_file_equip:
                    list_equipment = pd.read_csv(path_ings_links)
                else:
                    list_equipment['url'] = links_shortlist['Url']
                st.session_state.equipment = list_equipment


        with col23:
            if st.checkbox ("Items to Purchase", key = '5'):
                items_text = "  \n You love this recipe but you're not ready to try it just yet? Shop for *these handmade alternatives* in the following links:  \n  \n"
                for line in links_shortlist.itertuples():
                    items_text = items_text + f'{line[1]}  {line[2]}  \n'
                st.session_state.item_links = items_text

    container_tab1 = st.container (border = True)
    with container_tab1:
        # Building the texts from dataframes
        if len(st.session_state.ingredients) == 0:
            ings_text = ''    
        else:
            st.session_state.ingredients.to_csv(path_ings_links, index=False)
            ings_text = '  \n *Ingredients*  \n  \n'
            for row in st.session_state.ingredients.itertuples():
                if row[1] == 0:
                    line = f"{row[3]}"
                else:
                    line = f"{row[1]} {row[2]}   {row[3]}"
                if 'url' in st.session_state.ingredients.columns:
                    line = line + f"  {row[4]} \n"
                else:
                    line = line + f"  \n"
                ings_text = ings_text + line
        if len(st.session_state.equipment) == 0:
            equip_text = ''
        else:
            st.session_state.equipment.to_csv(path_equip_links, index=False)
            equip_text = '  \n *Equipment*  \n  \n'
            for row in st.session_state.equipment.itertuples():
                if 'url' in st.session_state.equipment.columns:
                    line = f"{row[1]}  {row[2]}  \n"
                else:
                    line = f"{row[1]}  \n"
                equip_text = equip_text + line
        items_text = st.session_state.item_links

        content_str = f"{desc_text}  \n {items_text}  \n {ings_text}   \n {equip_text}"
        new_text = st.text_area (f"Post title: {post_title}  \n  Recipe title: {recipe_title}  \n Final Description:",
            content_str,
            height = 500
            )


# Prepare text description for videos in Portuguese
with tab2:
    translator= Translator(to_lang="pt")
    # Interface to choose links
    st.write ("Choose links:")
    links = st.dataframe(
        affiliates_df[affiliates_df.Zone == 'PT'],
        height = 250,
        column_config={
            "name": st.column_config.TextColumn("name"),
            "url": st.column_config.TextColumn("URL")
        },
        hide_index=True,

        on_select="rerun",
        selection_mode="multi-row",
        )

    col1, col2 = st.columns (2)

    with col1:
        # List of links to add
        st.write ('Edit links table:')
        links_shortlist = st.data_editor(affiliates_df.iloc[links.selection['rows']], num_rows="dynamic", use_container_width=True, key='12')

        st.write ('Use file for:')
        col11, col12 = st.columns(2)
        with col11:
            check_file_ings = st.checkbox("Ingredients links", key='6')
        with col12:
            check_file_equip = st.checkbox("Equipment links", key='7')


    with col2: 
        st.write ('Final links list:')
        st.dataframe(links_shortlist, use_container_width=True)
        st.write ("Add links for:")

        col21, col22, col23 = st.columns(3)

        with col21:
            if st.checkbox ("Ingredients", key = '8'):
                if check_file_ings:
                    list_ingredients = pd.read_csv(path_ings_links)
                else:
                    list_ingredients['url'] = links_shortlist['Url']
                st.session_state.ingredients = list_ingredients

        with col22:
            if st.checkbox("Equipment", key = '9'):
                if check_file_equip:
                    list_equipment = pd.read_csv(path_ings_links)
                else:
                    list_equipment['url'] = links_shortlist['Url']
                st.session_state.equipment = list_equipment


        with col23:
            if st.checkbox ("Items to Purchase", key = '10'):
                items_text = "  \n You love this recipe but you're not ready to try it just yet? Shop for *these handmade alternatives* in the following links:  \n  \n"
                for line in links_shortlist.itertuples():
                    items_text = items_text + f'{line[1]}  {line[2]}  \n'
                st.session_state.item_links = items_text

    container_tab1 = st.container (border = True)
    with container_tab1:
        # Building the texts from dataframes
        if len(st.session_state.ingredients) == 0:
            ings_text = ''    
        else:
            st.session_state.ingredients.to_csv(path_ings_links, index=False)
            ings_text = '  \n *Ingredients*  \n  \n'
            for row in st.session_state.ingredients.itertuples():
                if row[1] == 0:
                    line = f"{row[3]}"
                else:
                    line = f"{row[1]} {row[2]}   {row[3]}"
                if 'url' in st.session_state.ingredients.columns:
                    line = line + f"  {row[4]} \n"
                else:
                    line = line + f"  \n"
                ings_text = ings_text + line
        if len(st.session_state.equipment) == 0:
            equip_text = ''
        else:
            st.session_state.equipment.to_csv(path_equip_links, index=False)
            equip_text = '  \n *Equipment*  \n  \n'
            for row in st.session_state.equipment.itertuples():
                if 'url' in st.session_state.equipment.columns:
                    line = f"{row[1]}  {row[2]}  \n"
                else:
                    line = f"{row[1]}  \n"
                equip_text = equip_text + line
        items_text = st.session_state.item_links

        desc_text_pt = translator.translate (desc_text)
        items_text_pt = translator.translate (items_text)
        ings_text_pt = translator.translate (ings_text)
        equip_text_pt = translator.translate (equip_text)

        content_str = f"{desc_text_pt}  \n {items_text_pt}  \n {ings_text_pt}   \n {equip_text_pt}"
        new_text = st.text_area (f"Post title: {post_title}  \n  Recipe title: {recipe_title}  \n Final Description:",
            content_str,
            height = 500
            )
