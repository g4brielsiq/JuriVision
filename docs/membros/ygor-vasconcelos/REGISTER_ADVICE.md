# Registro de Advogado - Endpoint de Cadastro

## Fluxo na interface

Na barra lateral, clique em **Criar conta** e informe nome completo, e-mail profissional, número da OAB e senha. Após a confirmação, o formulário de login abre com o e-mail do cadastro preenchido. Digite a senha para entrar.

## Visão geral
O endpoint `POST /api/v1/auth/register` cria a conta do advogado. O nome deve ter entre 2 e 150 caracteres, o e-mail deve ser válido e ter até 150 caracteres, e a senha deve ter entre 8 e 128 caracteres. A inscrição usa o formato número/UF com uma UF brasileira.

- **Método:** `POST`
- **URL:** `http://localhost:8000/api/v1/auth/register`
- **Formato de entrada:** JSON conforme o schema `RegisterRequest`.
- **Formato de saída:** JSON conforme o schema `RegisterResponse`.

## Exemplos de JSON

Entrada (`RegisterRequest`)

```json
{
  "nome": "Ygor Vasconcelos",
  "email": "ygor@example.com",
  "senha": "SenhaSegura123!",
  "numero_oab": "54321/AL"
}
```

Saída (`RegisterResponse`)

```json
{
  "id": "36c8cf77-d758-4636-881d-872dae63ffc8",
  "nome": "Ygor Vasconcelos",
  "email": "ygor@example.com",
  "oab": "54321/AL"
}
```

## Exemplo de Uso (cURL)
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
        "nome": "Ygor Vasconcelos",
        "email": "ygor@example.com",
        "senha": "SenhaSegura123!",
        "numero_oab": "54321/AL"
      }'
```

## Respostas
- **201 Created:** Cadastro efetuado com sucesso. Retorna os dados do usuário criado.
- **409 Conflict:** E-mail ou OAB já cadastrado.
- **422 Unprocessable Entity:** Dados de entrada inválidos.

## Notas de Implementação
- A API apara o nome e o e-mail, armazena o e-mail em minúsculas e normaliza a UF para maiúsculas.
- O banco garante a unicidade do e-mail e da inscrição. A OAB passa por validação de formato e unicidade local.
- A senha é armazenada como hash. O JWT é emitido no login em `POST /api/v1/auth/login`.
