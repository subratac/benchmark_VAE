import torch
import numpy as np
import torch.nn as nn
from typing import List

from pythae.models.nn import (
    BaseEncoder,
    BaseDecoder,
    BaseMetric,
    BaseDiscriminator,
    BaseLayeredDiscriminator
)
from ..base.base_utils import ModelOuput


class Encoder_AE_MLP(BaseEncoder):
    def __init__(self, args: dict):
        BaseEncoder.__init__(self)
        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim

        layers = nn.ModuleList()

        layers.append(
            nn.Sequential(nn.Linear(np.prod(args.input_dim), 512), nn.ReLU())
        )

        self.layers = layers
        self.depth = len(layers)

        self.embedding = nn.Linear(512, self.latent_dim)

    def forward(self, x, output_layer_levels:List[int]=None):
        output = ModelOuput()

        if output_layer_levels is not None:

            assert all(self.depth >= levels > 0), (
                f'Cannot output layer deeper than depth ({self.depth}) or with non-positive indice. '\
                f'Got ({output_layer_levels})'
                )


        out = x.reshape(-1, np.prod(self.input_dim))

        for i in range(self.depth):
            out = self.layers[i](out)

            if output_layer_levels is not None:
                if i+1 in output_layer_levels:
                    output[f'embedding_layer_{i+1}'] = out
        
        output['embedding'] = self.embedding(out)

        return output


class Encoder_VAE_MLP(BaseEncoder):
    def __init__(self, args: dict):
        BaseEncoder.__init__(self)
        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim

        layers = nn.ModuleList()

        layers.append(
            nn.Sequential(nn.Linear(np.prod(args.input_dim), 512), nn.ReLU())
        )

        self.layers = layers
        self.depth = len(layers)

        self.embedding = nn.Linear(512, self.latent_dim)
        self.log_var = nn.Linear(512, self.latent_dim)

    def forward(self, x, output_layer_levels:List[int]=None):
        output = ModelOuput()

        if output_layer_levels is not None:

            assert all(self.depth >= levels > 0), (
                f'Cannot output layer deeper than depth ({self.depth}) or with non-positive indice. '\
                f'Got ({output_layer_levels})'
                )


        out = x.reshape(-1, np.prod(self.input_dim))

        for i in range(self.depth):
            out = self.layers[i](out)

            if output_layer_levels is not None:
                if i+1 in output_layer_levels:
                    output[f'embedding_layer_{i+1}'] = out

        output['embedding'] = self.embedding(out)
        output['log_covariance'] = self.log_var(out)

        return output


class Decoder_AE_MLP(BaseDecoder):
    def __init__(self, args: dict):
        BaseDecoder.__init__(self)

        self.input_dim = args.input_dim

        # assert 0, np.prod(args.input_dim)

        layers = nn.ModuleList()

        layers.append(
            nn.Sequential(
                nn.Linear(args.latent_dim, 512),
                nn.ReLU()
            )
        )

        layers.append(
            nn.Sequential(
                nn.Linear(512, int(np.prod(args.input_dim))),
                nn.Sigmoid(),
            )
        )
       
        self.layers = layers
        self.depth = len(layers)


    def forward(self, z: torch.Tensor, output_layer_levels:List[int]=None):

        output = ModelOuput()

        if output_layer_levels is not None:

            assert all(self.depth >= levels > 0), (
                f'Cannot output layer deeper than depth ({self.depth}) or with non-positive indice. '\
                f'Got ({output_layer_levels})'
                )

        out = z

        for i in range(self.depth):
            out = self.layers[i](out)

            if output_layer_levels is not None:
                if i+1 in output_layer_levels:
                    output[f'reconstruction_layer_{i+1}'] = out

        output['reconstruction'] = out.reshape((z.shape[0],) + self.input_dim)

        return output


class Metric_MLP(BaseMetric):
    def __init__(self, args: dict):
        BaseMetric.__init__(self)

        if args.input_dim is None:
            raise AttributeError(
                "No input dimension provided !"
                "'input_dim' parameter of ModelConfig instance must be set to 'data_shape' where "
                "the shape of the data is [mini_batch x data_shape]. Unable to build metric "
                "automatically"
            )

        self.input_dim = args.input_dim
        self.latent_dim = args.latent_dim

        self.layers = nn.Sequential(nn.Linear(np.prod(args.input_dim), 512), nn.ReLU())
        self.diag = nn.Linear(512, self.latent_dim)
        k = int(self.latent_dim * (self.latent_dim - 1) / 2)
        self.lower = nn.Linear(512, k)

    def forward(self, x):

        h1 = self.layers(x.reshape(-1, np.prod(self.input_dim)))
        h21, h22 = self.diag(h1), self.lower(h1)

        L = torch.zeros((x.shape[0], self.latent_dim, self.latent_dim)).to(x.device)
        indices = torch.tril_indices(
            row=self.latent_dim, col=self.latent_dim, offset=-1
        )

        # get non-diagonal coefficients
        L[:, indices[0], indices[1]] = h22

        # add diagonal coefficients
        L = L + torch.diag_embed(h21.exp())

        output = ModelOuput(L=L)

        return output

class Discriminator_MLP(BaseDiscriminator):
    def __init__(self, args: dict):
        BaseDiscriminator.__init__(self)

        self.discriminator_input_dim = args.discriminator_input_dim

        self.layers = nn.Sequential(
            nn.Linear(np.prod(args.discriminator_input_dim), 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        out = self.layers(x.reshape(-1, np.prod(self.discriminator_input_dim)))

        output = ModelOuput(adversarial_cost=out)

        return output

class LayeredDiscriminator_MLP(BaseLayeredDiscriminator):
    def __init__(self, args: dict):
        
        self.discriminator_input_dim = args.discriminator_input_dim

        layers = nn.ModuleList()

        layers.append(
            nn.Sequential(
                nn.Linear(np.prod(args.discriminator_input_dim), 512),
                nn.ReLU()
            )
        )

        layers.append(
            nn.Linear(512, 256),
        )

        layers.append(
            nn.Sequential(
                nn.Linear(256, 1),
                nn.Sigmoid()
            )
        )

        BaseLayeredDiscriminator.__init__(self, layers=layers)

    def forward(self, x:torch.Tensor, output_layer_level:int=None):

        if output_layer_level is not None:

            assert output_layer_level <= self.depth, (
                f'Cannot output layer deeper ({output_layer_level}) than depth ({self.depth})'
            )

        x = x.reshape(x.shape[0], -1)

        for i in range(self.depth):
            x = self.layers[i](x)

            if i == output_layer_level:
                break
        
        output = ModelOuput(
            adversarial_cost=x
        )
    
        return output
