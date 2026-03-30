import requests
import json
import os
from openai import OpenAI
import gradio as gr

QWEN_API_KEY = os.getenv("QWEN_API_KEY", "ЗДЕСЬ_ТВОЙ_КЛЮЧ")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=QWEN_API_KEY)

def search_it_pro(role, salary, currency, exp, region, skills):
    url = "https://api.hh.ru/vacancies"
    area_id = 16 if region == "Беларусь" else 113
    strict_query = f"NAME:({role})"
    search_text = f"{strict_query} AND ({skills})" if skills else strict_query

    def fetch(with_filters=True):
        params = {
            "text": search_text, 
            "area": area_id, 
            "per_page": 10, 
            "order_by": "relevance",
            "search_field": "name"
        }
        if with_filters:
            if int(salary) > 0: params["salary"] = int(salary)
            params.update({"currency": currency, "experience": exp})
        res = requests.get(url, params=params, headers={'User-Agent': 'ProJobMatcher/7.0'})
        return res.json().get('items', [])

    items = fetch(with_filters=True)
    return items if items else fetch(with_filters=False)

def ai_expert_analysis(role, skills, vacancies):
    if not vacancies: return None
    short_list = []
    for i, v in enumerate(vacancies[:10]):
        short_list.append({
            "id": i, 
            "title": v['name'], 
            "company": v['employer']['name'], 
            "req": (v['snippet']['requirement'] or "")[:150]
        })
    
    prompt = f"Сравни требования в вакансиях с данными кандидата ({role}, стек {skills}). Выстави процент совпадения и дай короткий совет. Список: {json.dumps(short_list, ensure_ascii=False)}. Ответь ТОЛЬКО JSON: {{\"selections\": [{{\"id\": 0, \"match\": \"90%\", \"advice\": \"совет\"}}]}}"
    
    try:
        response = client.chat.completions.create(
            model="alibaba/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        clean_json = content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except:
        return {"selections": [{"id": i, "match": "---", "advice": "Анализ временно недоступен"} for i in range(len(vacancies[:5]))]}

custom_css = """
.gradio-container { background-color: #020617 !important; color: #f1f5f9 !important; }
.main-box { background: #0f172a !important; border: 1px solid #1e40af !important; border-radius: 12px; padding: 20px; }
.vac-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px; margin-bottom: 15px; border-left: 5px solid #3b82f6; }
.match-badge { background: #3b82f6; color: white; padding: 5px 15px; border-radius: 8px; font-weight: bold; }
.salary-tag { color: #34d399; font-weight: bold; float: right; }
.btn-search { background: #2563eb !important; color: white !important; font-weight: bold !important; height: 50px !important; }
"""

def run_pro_search(role, skills, sal, curr, reg, exp):
    raw_vacs = search_it_pro(role, sal, curr, exp, reg, skills)
    analysis = ai_expert_analysis(role, skills, raw_vacs)
    if not raw_vacs: return "Ничего не найдено.", ""
    
    html = ""
    analysis_data = analysis.get('selections', []) if analysis else []
    
    for i, v in enumerate(raw_vacs[:len(analysis_data)]):
        item = analysis_data[i]
        s = v.get('salary')
        sal_txt = f"{s['from'] if s.get('from') else ''}-{s['to'] if s.get('to') else ''} {s['currency']}" if s else "З/п не указана"
        html += f"""<div class="vac-card">
            <span class="salary-tag">{sal_txt}</span>
            <span class="match-badge">🔥 Совпадение: {item.get('match', 'N/A')}</span>
            <h3 style="color:#60a5fa; margin:0;">{v['name']}</h3>
            <p style="color:#94a3b8; margin:5px 0;">🏢 {v['employer']['name']} | 📍 {v['area']['name']}</p>
            <p style="color:#34d399;"><b>💡 Совет ИИ:</b> {item.get('advice', '')}</p>
            <a href="{v['alternate_url']}" target="_blank" style="display:inline-block; color:#3b82f6; text-decoration:none; font-weight:bold; border:1px solid #3b82f6; padding:5px 12px; border-radius:5px; margin-top:10px;">Смотреть вакансию →</a>
        </div>"""
    return f"Найдено вакансий: {len(raw_vacs)}", html

with gr.Blocks(css=custom_css) as demo:
    gr.HTML("<h2 style='text-align:center; color:#3b82f6;'>💎 AI IT Job Matcher</h2>")
    with gr.Row():
        with gr.Column(elem_classes="main-box"):
            role_in = gr.Textbox(label="Должность", value="Frontend Developer")
            skills_in = gr.Textbox(label="Навыки", value="React, JavaScript")
            sal_in = gr.Number(label="З/П от", value=0)
            curr_in = gr.Dropdown(choices=["USD", "BYN", "RUB"], value="USD", label="Валюта")
            reg_in = gr.Dropdown(choices=["Беларусь", "Россия"], value="Беларусь", label="Регион")
            exp_in = gr.Dropdown(choices=[("0 лет", "noExperience"), ("1-3 года", "between1And3"), ("3-6 лет", "between3And6")], value="between1And3", label="Опыт")
            search_btn = gr.Button("ПОИСК ЛУЧШИХ ВАКАНСИЙ", elem_classes="btn-search")
        with gr.Column():
            ai_out = gr.Markdown("Результаты анализа появятся здесь...")
            vac_out = gr.HTML("Ожидание поиска...")
    
    search_btn.click(run_pro_search, [role_in, skills_in, sal_in, curr_in, reg_in, exp_in], [ai_out, vac_out])

if __name__ == "__main__":
    demo.launch()
