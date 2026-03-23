from flask import render_template, request, jsonify

def registrar_modulos_profissionais(app, supabase, json_error, now_iso):
    # =========================
    # TELAS
    # =========================
    @app.route("/dashboard_geral")
    def dashboard_geral():
        return render_template("dashboard_geral.html")

    @app.route("/gestao_cadastro")
    def gestao_cadastro():
        return render_template("gestao_cadastro.html")

    @app.route("/gestao_tutoria")
    def gestao_tutoria():
        return render_template("gestao_tutoria.html")

    @app.route("/gestao_tutoria_agendamento")
    def gestao_tutoria_agendamento():
        return render_template("gestao_tutoria_agendamento.html")

    @app.route("/gestao_tutoria_atendimento")
    def gestao_tutoria_atendimento():
        return render_template("gestao_tutoria_atendimento.html")

    @app.route("/gestao_tutoria_ficha")
    def gestao_tutoria_ficha():
        return render_template("gestao_tutoria_ficha.html")

    @app.route("/gestao_tutoria_evolucao")
    def gestao_tutoria_evolucao():
        return render_template("gestao_tutoria_evolucao.html")

    @app.route("/gestao_frequencia_avancada")
    def gestao_frequencia_avancada():
        return render_template("gestao_frequencia_avancada.html")

    @app.route("/gestao_relatorio_frequencia_avancado")
    def gestao_relatorio_frequencia_avancado():
        return render_template("gestao_relatorio_frequencia_avancado.html")

    # =========================
    # DASHBOARD
    # =========================
    @app.route("/api/dashboard_geral")
    def api_dashboard_geral():
        try:
            ocorr = supabase.table("ocorrencias").select("numero", count="exact").execute()
            freq = supabase.table("f_frequencia").select("id,status", count="exact").execute()
            tut = supabase.table("atendimentos_tutoria").select("id", count="exact").execute()
            alunos = supabase.table("d_alunos").select("id", count="exact").execute()
            salas = supabase.table("d_salas").select("id", count="exact").execute()
            funcs = supabase.table("d_funcionarios").select("id", count="exact").execute()

            faltas = len([x for x in (freq.data or []) if x.get("status") == "F"])
            presencas = len([x for x in (freq.data or []) if x.get("status") == "P"])

            return jsonify({
                "ocorrencias": ocorr.count or 0,
                "frequencias": freq.count or 0,
                "presencas": presencas,
                "faltas": faltas,
                "atendimentos_tutoria": tut.count or 0,
                "alunos": alunos.count or 0,
                "salas": salas.count or 0,
                "funcionarios": funcs.count or 0
            })
        except Exception as e:
            return json_error(e)

    # =========================
    # CADASTRO
    # =========================
    @app.route("/api/cadastro/alunos")
    def api_cadastro_alunos():
        try:
            resp = supabase.table("d_alunos").select("*").execute()
            dados = resp.data or []

            alunos = []
            for a in dados:
                alunos.append({
                    "id": a.get("id"),
                    "nome": a.get("nome") or a.get("aluno_nome") or "",
                    "sala_nome": a.get("sala_nome") or "",
                    "tutor_nome": a.get("tutor_nome") or ""
                })

            alunos.sort(key=lambda x: x["nome"])
            return jsonify(alunos)
        except Exception as e:
            return json_error(e)

    @app.route("/api/cadastro/salas")
    @app.route("/api/salas")
    def api_cadastro_salas():
        try:
            resp = supabase.table("d_salas").select("*").execute()
            dados = resp.data or []

            salas = []
            for s in dados:
                salas.append({
                    "id": s.get("id"),
                    "nome": s.get("nome") or s.get("sala") or ""
                })

            salas.sort(key=lambda x: x["nome"])
            return jsonify(salas)
        except Exception as e:
            return json_error(e)

    @app.route("/api/cadastro/funcionarios")
    def api_cadastro_funcionarios():
        try:
            resp = supabase.table("d_funcionarios").select("*").execute()
            dados = resp.data or []

            funcionarios = []
            for f in dados:
                funcionarios.append({
                    "id": f.get("id"),
                    "nome": f.get("nome") or "",
                    "funcao": f.get("funcao") or "",
                    "email": f.get("email") or "",
                    "tipo": f.get("tipo") or ""
                })

            funcionarios.sort(key=lambda x: x["nome"])
            return jsonify(funcionarios)
        except Exception as e:
            return json_error(e)

    # =========================
    # APOIO PARA FREQUÊNCIA E TUTORIA
    # =========================
    @app.route("/api/alunos_por_sala/<int:sala_id>")
    def api_alunos_por_sala(sala_id):
        try:
            resp = supabase.table("d_alunos").select("*").eq("sala_id", sala_id).execute()
            dados = resp.data or []

            alunos = []
            for a in dados:
                alunos.append({
                    "id": a.get("id"),
                    "nome": a.get("nome") or a.get("aluno_nome") or "",
                    "sala_id": a.get("sala_id"),
                    "sala_nome": a.get("sala_nome") or "",
                    "tutor_id": a.get("tutor_id"),
                    "tutor_nome": a.get("tutor_nome") or ""
                })

            alunos.sort(key=lambda x: x["nome"])
            return jsonify(alunos)
        except Exception as e:
            return json_error(e)

    # =========================
    # TUTORIA
    # =========================
    @app.route("/api/tutores")
    def api_tutores():
        try:
            resp = supabase.table("d_funcionarios").select("*").execute()
            dados = resp.data or []

            tutores = []
            for f in dados:
                funcao = (f.get("funcao") or "").upper()
                tipo = (f.get("tipo") or "").upper()
                if "TUTOR" in funcao or tipo == "TUTOR":
                    tutores.append({
                        "id": f.get("id"),
                        "nome": f.get("nome") or "",
                        "funcao": f.get("funcao") or "",
                        "email": f.get("email") or ""
                    })

            tutores.sort(key=lambda x: x["nome"])
            return jsonify(tutores)
        except Exception as e:
            return json_error(e)

    @app.route("/api/alunos_tutoria")
    def api_alunos_tutoria():
        try:
            tutor_id = request.args.get("tutor_id")
            resp = supabase.table("d_alunos").select("*").execute()
            dados = resp.data or []

            alunos = []
            for a in dados:
                if tutor_id and str(a.get("tutor_id")) != str(tutor_id):
                    continue

                alunos.append({
                    "id": a.get("id"),
                    "nome": a.get("nome") or a.get("aluno_nome") or "",
                    "sala_nome": a.get("sala_nome") or "",
                    "tutor_id": a.get("tutor_id"),
                    "tutor_nome": a.get("tutor_nome") or ""
                })

            alunos.sort(key=lambda x: x["nome"])
            return jsonify(alunos)
        except Exception as e:
            return json_error(e)

    @app.route("/api/dashboard_tutoria")
    def api_dashboard_tutoria():
        try:
            tutores_resp = api_tutores().get_json()
            agend = supabase.table("agendamentos_tutoria").select("id,status", count="exact").execute()
            atend = supabase.table("atendimentos_tutoria").select("id", count="exact").execute()

            agendados = len([x for x in (agend.data or []) if (x.get("status") or "").upper() == "AGENDADO"])
            concluidos = len([x for x in (agend.data or []) if (x.get("status") or "").upper() == "CONCLUIDO"])

            return jsonify({
                "total_tutores": len(tutores_resp or []),
                "total_agendamentos": agend.count or 0,
                "agendados": agendados,
                "concluidos": concluidos,
                "total_atendimentos": atend.count or 0
            })
        except Exception as e:
            return json_error(e)

    @app.route("/api/agendamentos_tutoria")
    def api_agendamentos_tutoria():
        try:
            tutor_id = request.args.get("tutor_id")
            aluno_id = request.args.get("aluno_id")
            db = supabase.table("agendamentos_tutoria").select("*").order("data_agendamento").order("hora_agendamento")
            if tutor_id:
                db = db.eq("tutor_id", tutor_id)
            if aluno_id:
                db = db.eq("aluno_id", aluno_id)
            resp = db.execute()
            return jsonify(resp.data or [])
        except Exception as e:
            return json_error(e)

    @app.route("/api/agendar_tutoria", methods=["POST"])
    def api_agendar_tutoria():
        try:
            data = request.get_json() or {}
            payload = {
                "tutor_id": data.get("tutor_id"),
                "tutor_nome": data.get("tutor_nome"),
                "aluno_id": data.get("aluno_id"),
                "aluno_nome": data.get("aluno_nome"),
                "sala_nome": data.get("sala_nome"),
                "tema": data.get("tema"),
                "observacao": data.get("observacao"),
                "status": data.get("status") or "AGENDADO",
                "data_agendamento": data.get("data"),
                "hora_agendamento": data.get("hora"),
                "created_at": now_iso()
            }
            if not payload["tutor_id"] or not payload["aluno_id"] or not payload["data_agendamento"] or not payload["hora_agendamento"]:
                return json_error("Preencha tutor, aluno, data e hora.", 400)
            resp = supabase.table("agendamentos_tutoria").insert(payload).execute()
            return jsonify({"success": True, "data": resp.data})
        except Exception as e:
            return json_error(e)

    @app.route("/api/atendimentos_tutoria")
    def api_atendimentos_tutoria():
        try:
            tutor_id = request.args.get("tutor_id")
            aluno_id = request.args.get("aluno_id")
            db = supabase.table("atendimentos_tutoria").select("*").order("data_registro", desc=True)
            if tutor_id:
                db = db.eq("tutor_id", tutor_id)
            if aluno_id:
                db = db.eq("aluno_id", aluno_id)
            resp = db.execute()
            return jsonify(resp.data or [])
        except Exception as e:
            return json_error(e)

    @app.route("/api/salvar_atendimento_tutoria", methods=["POST"])
    def api_salvar_atendimento_tutoria():
        try:
            data = request.get_json() or {}
            payload = {
                "tutor_id": data.get("tutor_id"),
                "tutor_nome": data.get("tutor_nome"),
                "aluno_id": data.get("aluno_id"),
                "aluno_nome": data.get("aluno_nome"),
                "sala_nome": data.get("sala_nome"),
                "tipo_atendimento": data.get("tipo_atendimento"),
                "encaminhamento": data.get("encaminhamento"),
                "registro": data.get("registro"),
                "proximos_passos": data.get("proximos_passos"),
                "data_registro": now_iso()
            }
            if not payload["tutor_id"] or not payload["aluno_id"] or not payload["registro"]:
                return json_error("Preencha tutor, aluno e registro.", 400)
            resp = supabase.table("atendimentos_tutoria").insert(payload).execute()
            return jsonify({"success": True, "data": resp.data})
        except Exception as e:
            return json_error(e)

    @app.route("/api/ficha_tutoria/<int:aluno_id>")
    def api_ficha_tutoria(aluno_id):
        try:
            aluno_resp = supabase.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
            if not aluno_resp.data:
                return json_error("Aluno não encontrado", 404)
            aluno = aluno_resp.data[0]
            ocorr_resp = supabase.table("ocorrencias").select("numero,data_hora,descricao,status,pendencia").eq("aluno_id", aluno_id).order("numero", desc=True).limit(50).execute()
            atend_resp = supabase.table("atendimentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_registro", desc=True).limit(50).execute()
            agend_resp = supabase.table("agendamentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_agendamento", desc=True).limit(50).execute()
            freq_resp = supabase.table("f_frequencia").select("*").eq("aluno_id", aluno_id).order("data", desc=True).limit(100).execute()
            notas_resp = supabase.table("notas_aluno").select("*").eq("aluno_id", aluno_id).execute()
            return jsonify({
                "aluno": aluno,
                "ocorrencias": ocorr_resp.data or [],
                "atendimentos": atend_resp.data or [],
                "agendamentos": agend_resp.data or [],
                "frequencia": freq_resp.data or [],
                "notas": notas_resp.data or []
            })
        except Exception as e:
            return json_error(e)

    @app.route("/api/evolucao_aluno/<int:aluno_id>")
    def api_evolucao_aluno(aluno_id):
        try:
            freq_resp = supabase.table("f_frequencia").select("*").eq("aluno_id", aluno_id).order("data", desc=False).execute()
            ocorr_resp = supabase.table("ocorrencias").select("numero,data_hora,descricao,status").eq("aluno_id", aluno_id).order("data_hora", desc=False).execute()
            freq = freq_resp.data or []
            ocorr = ocorr_resp.data or []
            resumo = {
                "presencas": len([x for x in freq if x.get("status") == "P"]),
                "faltas": len([x for x in freq if x.get("status") == "F"]),
                "atrasos": len([x for x in freq if x.get("status") in ["PA", "PSA"]]),
                "saidas": len([x for x in freq if x.get("status") in ["PS", "PSA"]]),
                "ocorrencias": len(ocorr)
            }
            return jsonify({"resumo": resumo, "frequencia": freq, "ocorrencias": ocorr})
        except Exception as e:
            return json_error(e)

    # =========================
    # FREQUÊNCIA AVANÇADA
    # =========================
    @app.route("/api/frequencia/listar")
    def api_frequencia_listar():
        try:
            sala_id = request.args.get("sala_id")
            data_ref = request.args.get("data")
            resp = supabase.table("f_frequencia").select("*").eq("sala_id", sala_id).eq("data", data_ref).execute()
            return jsonify(resp.data or [])
        except Exception as e:
            return json_error(e)

    @app.route("/api/frequencia/salvar", methods=["POST"])
    def api_frequencia_salvar():
        try:
            registros = request.get_json() or []
            resp = supabase.table("f_frequencia").upsert(registros).execute()
            return jsonify({"success": True, "data": resp.data})
        except Exception as e:
            return json_error(e)

    @app.route("/api/frequencia/relatorio")
    def api_frequencia_relatorio():
        try:
            sala_id = request.args.get("sala_id")
            resp = supabase.table("f_frequencia").select("*").eq("sala_id", sala_id).execute()
            return jsonify(resp.data or [])
        except Exception as e:
            return json_error(e)