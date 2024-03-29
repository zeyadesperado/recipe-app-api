"""
Tests for the Recipe APIs.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)

RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """helper function to create and return a sample recipe."""
    defaults = {
        "title": "this is a sample title",
        "time_minutes": 22,
        "price": Decimal('5.25'),
        "description": "this is sample description",
        "link": "https://fb.com/zeyadesperado",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated api requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """test auth is required to call apis."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    """Test authetincated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@example.com", password="test123")
        self.user = get_user_model().objects.create_user(
            'test@example.com',
            'testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipe."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user"""
        other_user = create_user(email='other@example.com', password='test123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe details."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_recipe(self):
        """Test creating a recipe."""
        payload = {
            'title': 'simple recipe title',
            'time_minutes': 15,
            'price': Decimal('5.99'),
            'description': 'how to make the recipe',
            'link': "fb.com/zeyadesperado",
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update for the recipe"""
        original_link = "www.example.com"
        recipe = create_recipe(
            user=self.user,
            title='Sample title for recipe',
            link=original_link,
        )
        payload = {"title": "New Recipe title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample Title',
            link="www.example.com",
            description='sample descipe'
        )
        payload = {
            "title": "new recipe title",
            "link": "www.examplenew.com",
            "description": "new descipetion",
            "time_minutes": 10,
            "price": Decimal("5.99"),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)

        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successfuly."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
