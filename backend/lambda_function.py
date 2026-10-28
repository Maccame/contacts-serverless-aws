import json
import boto3
import uuid
from datetime import datetime, timezone

ddb = boto3.resource("dynamodb")
table = ddb.Table("contacts")


def handler(event, context):
    print("Event reçu:", json.dumps(event))

    method = event.get("httpMethod")
    path_params = event.get("pathParameters") or {}
    contact_id = path_params.get("id")

    try:
        # POST /contacts
        if method == "POST":
            body = json.loads(event.get("body") or "{}")
            item = {**body, "id": str(uuid.uuid4()), "createdAt": datetime.now(timezone.utc).isoformat()}
            table.put_item(Item=item)
            return resp(201, item)

        # GET /contacts
        if method == "GET" and not contact_id:
            result = table.scan()
            return resp(200, result["Items"])

        # GET /contacts/{id}
        if method == "GET" and contact_id:
            result = table.get_item(Key={"id": contact_id})
            item = result.get("Item")
            if not item:
                return resp(404, {"message": "Contact non trouvé"})
            return resp(200, item)

        # PUT /contacts/{id}
        if method == "PUT" and contact_id:
            body = json.loads(event.get("body") or "{}")
            champs = {k: body[k] for k in ("nom", "email", "message") if k in body}
            if not champs:
                return resp(400, {"message": "Aucun champ à modifier (nom, email, message)"})
            champs["updatedAt"] = datetime.now(timezone.utc).isoformat()

            expression = "SET " + ", ".join(f"#{k} = :{k}" for k in champs)
            noms = {f"#{k}": k for k in champs}
            valeurs = {f":{k}": v for k, v in champs.items()}

            try:
                result = table.update_item(
                    Key={"id": contact_id},
                    UpdateExpression=expression,
                    ConditionExpression="attribute_exists(id)",
                    ExpressionAttributeNames=noms,
                    ExpressionAttributeValues=valeurs,
                    ReturnValues="ALL_NEW",
                )
            except table.meta.client.exceptions.ConditionalCheckFailedException:
                return resp(404, {"message": "Contact non trouvé"})

            return resp(200, result["Attributes"])

        # DELETE /contacts/{id}
        if method == "DELETE" and contact_id:
            table.delete_item(Key={"id": contact_id})
            return resp(200, {"message": "Contact supprimé"})

        return resp(405, {"message": "Méthode non supportée"})

    except Exception as e:
        print("Erreur:", str(e))
        return resp(500, {"message": "Erreur interne", "detail": str(e)})


def resp(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }
