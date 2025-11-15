# ==============================================================================
# MOTOR DE EXECUÇÃO DE PLANILHAS (Flask App) - V7
# Arquiteto: Seu "Sócio-Técnico (CTO)" da IA
# ==============================================================================

import sys
import io
import os
import uuid  # V7: Essencial para nomes de arquivos únicos (evita race condition)
import traceback  # V7: Essencial para "debugar" o que a IA fez

from flask import Flask, request, send_file, jsonify

# Nossas "ferramentas pesadas" (da lista requirements.txt)
# As importamos aqui para passá-las ao "sandbox"
import openpyxl
import pandas

app = Flask(__name__)

# ==============================================================================
# O "SANDBOX" (A Jaula de Segurança) - V7
# ==============================================================================

# V7: Esta é a melhoria de segurança mais importante.
# O script da IA SÓ terá acesso ao que estiver neste dicionário.
# Ele NÃO terá acesso a 'os', 'sys', 'subprocess', 'eval', etc.
RESTRICTED_GLOBALS = {
    "__builtins__": {
        # Permite funções Python seguras e básicas
        "print": print,
        "range": range,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "list": list,
        "dict": dict,
        "True": True,
        "False": False,
        "None": None,
    },
    # Permite as bibliotecas de planilha que a IA precisa
    "openpyxl": openpyxl,
    "pandas": pandas,
    "io": io,
}

# ==============================================================================
# O "ENDPOINT" (O Portão da Fábrica)
# ==============================================================================

# Este é o "portão" da nossa fábrica: /execute
# O N8N vai "chamar" este endereço
@app.route("/execute", methods=["POST"])
def execute_script():
    
    # V7: Cria um nome de arquivo ÚNICO para esta requisição.
    # Isso resolve a "race condition" (Falha de Concorrência).
    # Usamos /tmp/ (se disponível) ou o diretório local.
    temp_dir = "/tmp" if os.path.isdir("/tmp") else os.getcwd()
    output_filename = os.path.join(temp_dir, f"{uuid.uuid4()}.xlsx")

    try:
        # 1. Pega a "ordem de serviço" (o script) que o N8N enviou
        data = request.get_json()
        if "script" not in data:
            return jsonify({"error": "Nenhum 'script' foi fornecido."}), 400

        ai_script = data["script"]

        # 2. Prepara o "escopo local" para o script da IA
        # V7: Passamos o nome do arquivo *para dentro* do script.
        custom_locals = {
            "output_filename": output_filename
        }

        # 3. Executa o script da IA DENTRO DO SANDBOX (V7)
        # O 'exec' vai usar o openpyxl/pandas e o 'output_filename'
        exec(ai_script, RESTRICTED_GLOBALS, custom_locals)

        # 4. Verifica se o arquivo foi realmente criado
        if not os.path.exists(output_filename):
            # Se o script da IA falhou (deu erro), avisa o N8N
            return jsonify({"error": "O script da IA executou sem erros, mas falhou em criar o 'output.xlsx'."}), 500

        # 5. Se o arquivo foi criado, lê o arquivo do disco...
        with open(output_filename, "rb") as f:
            file_data = f.read()

        # 6. ...e o envia de volta para o N8N como um arquivo .xlsx
        return send_file(
            io.BytesIO(file_data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="planilha_gerada.xlsx"
        )

    except Exception as e:
        # 7. (V7) Se *qualquer* coisa der errado, avisa o N8N
        # com o máximo de detalhes (traceback) para "debugar"
        error_details = traceback.format_exc()
        return jsonify({
            "error": f"Falha na execução: {str(e)}",
            "traceback": error_details,
            "script_que_falhou": ai_script  # Loga o script exato que falhou
        }), 500
        
    finally:
        # 8. Limpa a "bagunça" (apaga o arquivo temporário)
        # O 'finally' garante que isso rode mesmo se o 'try' falhar
        if os.path.exists(output_filename):
            os.remove(output_filename)

# Esta linha é necessária para o Render "ligar" o servidor da fábrica
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
