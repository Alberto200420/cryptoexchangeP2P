# Import necessary modules and classes from Django
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Define a custom manager for the User model
class UserAccountManager(BaseUserManager):
    # Define a method to create a regular user
    def create_user(self, email, password=None, **extra_fields):
        # Check if email is provided
        if not email:
            raise ValueError("Users must have an email address")

        # Normalize the email (convert to lowercase)
        email = self.normalize_email(email)
        email = email.lower()
        
        # Create a new user instance with the provided information
        user = self.model(email=email, **extra_fields)
        
        # Set the user's password
        user.set_password(password)
        
        # Save the user in the database
        user.save(using=self._db)

        # Return the created user
        return user
    
    # Define a method to create a superuser
    def create_superuser(self, email, password, **extra_fields):
        # Create a regular user first
        user = self.create_user(email, password, **extra_fields)

        # Set additional attributes for a superuser
        user.is_superuser = True
        user.is_staff = True
        user.role = "Owner"
        # user.verified = True

        # Save the user in the database
        user.save(using=self._db)

        # Return the created superuser
        return user

# Define the UserAccount model, inheriting from AbstractBaseUser and PermissionsMixin
class UserAccount(AbstractBaseUser, PermissionsMixin):
    # Define roles as a set of choices
    roles = (
        {'user_basic', 'User_basic'},
        {'owner', 'Owner'},
        {'moderator', 'Moderator'},
    )

    # Define fields for the UserAccount model
    email =         models.EmailField(unique=True, max_length=70)
    first_name =    models.CharField(max_length=40)
    last_name =     models.CharField(max_length=40)
    is_active =     models.BooleanField(default=True)
    is_online =     models.BooleanField(default=False)
    is_staff =      models.BooleanField(default=False)
    is_superuser =  models.BooleanField(default=False)
    role =          models.CharField(max_length=25, choices=roles, default='user_basic')
    # verified =      models.BooleanField(default=False)

    # Use the custom manager for the User model
    objects = UserAccountManager()

    # Define the email field as the USERNAME_FIELD
    USERNAME_FIELD = 'email'

    # Define additional fields required for creating a user
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Define a string representation of the user (for debugging and display)
    def __str__(self):
        return self.email
