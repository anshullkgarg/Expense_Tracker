from groups.models import GroupToUser, Group
import json
from datetime import date, datetime
from decimal import Decimal
from rest_framework.renderers import JSONRenderer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login
import jwt
from users import serializers, models
from users.models import User
from users.serializers import signInUserSerializer, UserProfileSerializer
import datetime
import django.core.management.commands.runserver as runserver


class CreateUserAPIView(APIView):
    serializer_class = serializers.UserProfileSerializer

    def post(self, request) -> Response:
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            name = serializer.validated_data.get('first_name')
            return Response({'message': f'user {name} created successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JsonENcoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime) or isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return str(obj)
        else:
            return super().default(obj)


class getUserList(APIView):
    renderer_classes = [JSONRenderer]

    def get(self, request):
        try:
            _user_data = models.User.objects.values_list('first_name', 'last_name', 'email')
            _user_list = list(_user_data)
            content1 = {'_user_list': _user_list}

            return Response(content1)
        except Exception as e:
            print(e)
            error_msg = "Internal Error Occurred"
            return Response(json.dumps({
                'message': error_msg,
                'status': 'fail'
            }, cls=JsonENcoder), status=500)


def check_user_login_or_not(request):
    token = request.COOKIES.get('jwt')
    if not token:
        raise AuthenticationFailed('Unauthenticated!')
    try:
        payload = jwt.decode(token, 'secret', algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed('Unauthenticated!')
    return payload


class signIn(APIView):
    serializer_class = signInUserSerializer

    def post(self, request) -> Response:
        print(request)
        email = request.POST['email']
        password = request.POST['password']
        print(email)
        print(password)
        user = models.User.objects.filter(email=email).first()

        if user.check_password(password) is not None:
            print("Hello")
        if user is None:
            raise AuthenticationFailed("User not found")
        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect Password")

        payload = {
            'id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            'iat': datetime.datetime.utcnow()
        }

        token = jwt.encode(payload, 'secret', algorithm='HS256')
        response = Response()
        cmd = runserver.Command()

        response.set_cookie(key='jwt', value=token, httponly=True)
        response.data = {
            'jwt': token,
            'url': 'http://' + str(cmd.default_addr) + ':' + str(cmd.default_port)+"/users/" + str(user.id) + "/profile/"
        }
        login(request, user)

        return response


class UserView(APIView):

    def get(self, request):
        payload = check_user_login_or_not(request)
        user = User.objects.filter(id=payload['id']).first()
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)


class LogoutView(APIView):
    def get(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {
            'message': 'success'
        }
        return response


class Profile(APIView):
    def get(self, request, pk):

        payload = check_user_login_or_not(request)
        _user_id = payload['id']
        _user_obj = User.objects.filter(id=_user_id).values()

        _group_obj_list = GroupToUser.objects.filter(user_id=_user_id).values_list('group_id', flat=True)
        _list_group_id = list(_group_obj_list)
        print(_list_group_id)
        _group_data = Group.objects.filter(id__in=_list_group_id).values()

        print(_group_data)
        _user_obj = list(_user_obj)[0]
        print(len(_user_obj))
        _user_obj['groups'] = _group_data
        return Response(_user_obj)
