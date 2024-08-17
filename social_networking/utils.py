from rest_framework.response import Response

def custom_response(message, data, status_code):
    return Response({
        "message": message,
        "data": data,
        "status_code": status_code
    }, status=status_code)