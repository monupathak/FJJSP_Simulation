"""DQN agent with target network, replay buffer, and gradient-based updates."""

import random
from collections import deque
from typing import Any, Deque, Iterable, List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim


class DQNNetwork(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DQNAgent:
    def __init__(
        self,
        action_space: Iterable[str],
        epsilon_scheduler: Any,
        replay_capacity: int = 5000,
        minibatch_size: int = 64,
        gamma: float = 0.99,
        lr: float = 1e-3,
        target_sync: int = 10,
        grad_clip: float = 1.0,
        input_dim: int = 3,
    ):
        self.action_space = list(action_space)
        self.action_to_idx = {a: i for i, a in enumerate(self.action_space)}
        self.epsilon_scheduler = epsilon_scheduler
        self.replay_buffer: Deque[Tuple[Any, str, float, Any, bool]] = deque(maxlen=replay_capacity)
        self.minibatch_size = minibatch_size
        self.gamma = gamma
        self.grad_clip = grad_clip
        self.target_sync = target_sync
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.online_net = DQNNetwork(input_dim, len(self.action_space)).to(self.device)
        self.target_net = DQNNetwork(input_dim, len(self.action_space)).to(self.device)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.optimizer = optim.Adam(self.online_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.update_steps = 0

    @property
    def epsilon(self) -> float:
        return getattr(self.epsilon_scheduler, "epsilon", 1.0)

    def select_strategy(self, state_vector: Any) -> str:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.choice(self.action_space)

        state_tensor = self._to_tensor(state_vector).unsqueeze(0)  # [1, input_dim]
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
            action_idx = int(torch.argmax(q_values, dim=1).item())
        return self.action_space[action_idx]

    def store_experience(
        self,
        state_vector: Any,
        action: str,
        reward: float,
        next_state_vector: Any,
        done: bool = False,
    ) -> None:
        self.replay_buffer.append((state_vector, action, reward, next_state_vector, done))
        self.train_step()

    def train_step(self) -> None:
        if len(self.replay_buffer) < self.minibatch_size:
            return

        batch = random.sample(self.replay_buffer, self.minibatch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        state_batch = self._to_tensor(states)
        next_state_batch = self._to_tensor(next_states)
        reward_batch = torch.tensor(rewards, dtype=torch.float32, device=self.device)
        done_batch = torch.tensor(dones, dtype=torch.float32, device=self.device)

        action_indices = torch.tensor(
            [self.action_to_idx[a] for a in actions], dtype=torch.int64, device=self.device
        )

        # Q(s, a)
        q_values = self.online_net(state_batch).gather(1, action_indices.unsqueeze(1)).squeeze(1)

        # max_a' Q_target(s', a')
        with torch.no_grad():
            next_q_values = self.target_net(next_state_batch).max(dim=1)[0]
            targets = reward_batch + self.gamma * (1 - done_batch) * next_q_values

        loss = self.loss_fn(q_values, targets)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online_net.parameters(), self.grad_clip)
        self.optimizer.step()

        self.update_steps += 1
        if self.update_steps % self.target_sync == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())

    def _to_tensor(self, state: Any) -> torch.Tensor:
        """Convert state tuple(s) to a float32 tensor."""
        if isinstance(state, (list, tuple)):
            if len(state) > 0 and isinstance(state[0], (list, tuple, float, int)):
                return torch.tensor(state, dtype=torch.float32, device=self.device)
        return torch.tensor(state, dtype=torch.float32, device=self.device)
